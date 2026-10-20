from src.modules.channels.application.content_update.port.plugin import (
    ContentUpdatePlugin,
)
from src.modules.channels.application.port.plugin_services import (
    PluginContentHttpTransport,
)
from typing import Protocol
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


class PluginRegistryProtocol(Protocol):
    """Разрешает capabilities без знания общего ядра о platform kind."""

    def manifests(self) -> tuple[PluginManifestDTO, ...]:
        """Возвращает только зарегистрированные реализации."""
        ...

    def manifest(self, kind: str) -> PluginManifestDTO:
        """Возвращает контракт поддержанного плагина либо отказ."""
        ...

    def validate(
        self,
        kind: str,
        settings: ResourceSettingsDTO,
        credentials: dict[str, str] | None,
    ) -> ConnectionSettingsReferencesDTO:
        """Проверяет форму конфигурации и credentials плагина."""
        ...

    def verifier(
        self, kind: str, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> VerifyConnectionPlugin:
        """Собирает проверку на ограниченных фасадах."""
        ...

    def reader(
        self, kind: str, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationPagePlugin:
        """Собирает read capability на ограниченных фасадах."""
        ...

    def detail_reader(
        self, kind: str, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationDetailsPlugin:
        """Собирает полное чтение одной публикации через зарегистрированный плагин."""
        ...

    def content_updater(
        self,
        kind: str,
        credentials: PluginCredentialsAccess,
        http: PluginContentHttpTransport,
    ) -> ContentUpdatePlugin:
        """Собирает capability предпросмотра и ограниченного обновления."""
        ...
