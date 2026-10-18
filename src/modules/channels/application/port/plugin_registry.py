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
    ) -> None:
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
