from typing import Protocol
from src.modules.channels.application.plugin_contract import (
    PluginManifestDTO,
    ResourceSettingsDTO,
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
from src.modules.channels.domain.error import (
    ChannelsUnavailableError,
    ChannelsValidationError,
)


class PluginFactoryProtocol(Protocol):
    """Определяет внешнюю сборку provider-пакета для реестра."""

    manifest: PluginManifestDTO

    def validate(
        self, settings: ResourceSettingsDTO, credentials: dict[str, str] | None
    ) -> None:
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


class PluginRegistry:
    """Разрешает явно зарегистрированные реализации без ветвлений по kind."""

    def __init__(self, factories: tuple[PluginFactoryProtocol, ...]) -> None:
        """Отклоняет дубликаты и несовместимый SDK до обработки запросов."""
        self._factories: dict[str, PluginFactoryProtocol] = {}
        for factory in factories:
            manifest = factory.manifest
            if (
                manifest.kind in self._factories
                or manifest.sdk_version != 1
                or set(manifest.capabilities)
                != {"verify_connection", "read_publications"}
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
    ) -> None:
        """Делегирует форму provider factory."""
        self._factory(kind).validate(settings, credentials)

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
