from pydantic import ValidationError
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
from src.modules.channels.domain.error import ChannelsValidationError
from src.modules.channels.infrastructure.plugin.prom.manifest import (
    MANIFEST,
    PromCredentials,
)
from src.modules.channels.infrastructure.plugin.prom.verify_connection import (
    PromVerifyConnectionPlugin,
)
from src.modules.channels.infrastructure.plugin.prom.read_publication_page import (
    PromReadPublicationPagePlugin,
)


class PromPluginFactory:
    """Собирает реализованные read capabilities Prom.ua."""

    manifest: PluginManifestDTO = MANIFEST

    def validate(
        self, settings: ResourceSettingsDTO, credentials: dict[str, str] | None
    ) -> None:
        """Проверяет настройки и секретную форму без внешних вызовов."""
        if settings.endpoint != "https://my.prom.ua":
            raise ChannelsValidationError("prom_endpoint_must_be_my_prom_ua")
        if credentials is not None:
            try:
                PromCredentials.model_validate(credentials)
            except ValidationError:
                raise ChannelsValidationError("invalid_credentials_shape") from None

    def verifier(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> VerifyConnectionPlugin:
        """Создаёт scoped проверку доступа."""
        return PromVerifyConnectionPlugin(credentials, http)

    def reader(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationPagePlugin:
        """Создаёт scoped чтение публикаций."""
        return PromReadPublicationPagePlugin(credentials, http)
