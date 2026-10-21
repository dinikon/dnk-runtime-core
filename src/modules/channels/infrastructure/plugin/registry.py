from src.modules.channels.application.batch_export.plugin_contract import (
    BatchExportPlugin,
)
from src.modules.channels.application.port.plugin_services import (
    PluginBatchHttpTransport,
)
from src.modules.channels.application.content_update.port.plugin import (
    ContentUpdatePlugin,
)
from src.modules.channels.application.port.plugin_services import (
    PluginContentHttpTransport,
)
from typing import Protocol, runtime_checkable
from src.modules.channels.application.plugin_contract import (
    PluginManifestDTO,
    ResourceSettingsDTO,
    ConnectionSettingsReferencesDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
)
from src.modules.channels.application.channel.port.verify_connection_plugin import (
    VerifyConnectionPlugin,
)
from src.modules.channels.application.external_publication.port.read_publication_page_plugin import (
    ReadPublicationPagePlugin,
)
from src.modules.channels.application.external_publication.port.read_publication_details_plugin import (
    ReadPublicationDetailsPlugin,
)

from src.modules.channels.domain.error import (
    ChannelsUnavailableError,
    ChannelsValidationError,
)


class PluginFactoryProtocol(Protocol):
    """Определяет внешнюю сборку provider-пакета для реестра."""

    manifest: PluginManifestDTO

    def validate(
        self, settings: ResourceSettingsDTO, credentials: dict[str, str] | None
    ) -> ConnectionSettingsReferencesDTO:
        """Проверяет конкретную конфигурацию."""
        ...

    def verifier(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> VerifyConnectionPlugin:
        """Собирает verification capability."""
        ...

    def reader(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationPagePlugin:
        """Собирает read capability."""
        ...

    def detail_reader(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationDetailsPlugin:
        """Собирает полное чтение содержимого."""
        ...

    def content_updater(
        self, credentials: PluginCredentialsAccess, http: PluginContentHttpTransport
    ) -> ContentUpdatePlugin:
        """Собирает проверку и ограниченную запись контента."""
        ...


@runtime_checkable
class BatchExportPluginFactoryProtocol(Protocol):
    """Описывает только опциональную capability; остальные плагины не обязаны её реализовывать."""

    def batch_exporter(
        self, credentials: PluginCredentialsAccess, http: PluginBatchHttpTransport
    ) -> BatchExportPlugin:
        """Собирает опциональную пакетную capability."""
        ...


class PluginRegistry:
    """Разрешает явно зарегистрированные реализации без ветвлений по kind."""

    def __init__(self, factories: tuple[PluginFactoryProtocol, ...]) -> None:
        """Отклоняет дубликаты и несовместимый SDK до обработки запросов."""
        self._factories: dict[str, PluginFactoryProtocol] = {}
        for factory in factories:
            manifest = factory.manifest
            if (
                (
                    "batch_content_export" in manifest.capabilities
                    and not isinstance(factory, BatchExportPluginFactoryProtocol)
                )
                or manifest.kind in self._factories
                or manifest.sdk_version != 5
                or manifest.config_version != 3
                or (
                    (manifest.publication_identity is not None)
                    != ("publication_identity_diagnostics" in manifest.capabilities)
                )
                or (
                    manifest.publication_identity is not None
                    and (
                        not manifest.publication_identity.key_path
                        or any(
                            not segment or not isinstance(segment, str)
                            for segment in manifest.publication_identity.key_path
                        )
                    )
                )
                or not {"verify_connection", "read_publications"}
                <= set(manifest.capabilities)
                or not set(manifest.capabilities)
                <= {
                    "verify_connection",
                    "read_publications",
                    "read_publication_details",
                    "preview_content_update",
                    "update_content",
                    "publication_identity_diagnostics",
                    "batch_content_export",
                }
            ):
                raise ChannelsValidationError("invalid_plugin_registration")
            self._factories[manifest.kind] = factory

    def manifests(self) -> tuple[PluginManifestDTO, ...]:
        """Возвращает реализованные плагины в стабильном порядке."""
        return tuple((factory.manifest for factory in self._factories.values()))

    def _factory(self, kind: str) -> PluginFactoryProtocol:
        """Возвращает реализацию либо явную unavailable причину."""
        if kind not in self._factories:
            raise ChannelsUnavailableError("plugin_not_installed")
        return self._factories[kind]

    def manifest(self, kind: str) -> PluginManifestDTO:
        """Возвращает manifest одной реализации."""
        return self._factory(kind).manifest

    def validate(
        self,
        kind: str,
        settings: ResourceSettingsDTO,
        credentials: dict[str, str] | None,
    ) -> ConnectionSettingsReferencesDTO:
        """Проверяет общую policy manifest и делегирует provider-specific форму."""
        return self._factory(kind).validate(settings, credentials)

    def verifier(
        self, kind: str, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> VerifyConnectionPlugin:
        """Собирает verify реализацию текущего scope."""
        return self._factory(kind).verifier(credentials, http)

    def reader(
        self, kind: str, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationPagePlugin:
        """Собирает read реализацию текущего scope."""
        return self._factory(kind).reader(credentials, http)

    def detail_reader(
        self, kind: str, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationDetailsPlugin:
        """Проверяет capability до создания runtime для выбранного ресурса."""
        factory = self._factory(kind)
        if "read_publication_details" not in factory.manifest.capabilities:
            raise ChannelsUnavailableError("publication_details_unsupported")
        return factory.detail_reader(credentials, http)

    def content_updater(
        self,
        kind: str,
        credentials: PluginCredentialsAccess,
        http: PluginContentHttpTransport,
    ) -> ContentUpdatePlugin:
        """Разрешает capability без ветвления общего ядра по платформе."""
        factory = self._factory(kind)
        if "preview_content_update" not in factory.manifest.capabilities:
            raise ChannelsUnavailableError("content_update_unsupported")
        return factory.content_updater(credentials, http)

    def batch_exporter(
        self,
        kind: str,
        credentials: PluginCredentialsAccess,
        http: PluginBatchHttpTransport,
    ) -> BatchExportPlugin:
        """Разрешает пакетную capability по manifest без условий платформы в ядре."""
        factory = self._factory(kind)
        if "batch_content_export" not in factory.manifest.capabilities:
            raise ChannelsUnavailableError("batch_export_unsupported")
        if not isinstance(factory, BatchExportPluginFactoryProtocol):
            raise ChannelsUnavailableError("batch_export_unsupported")
        return factory.batch_exporter(credentials, http)
