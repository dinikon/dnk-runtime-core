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
from src.modules.channels.infrastructure.plugin.woocommerce.manifest import (
    MANIFEST,
    WooCredentials,
)
from src.modules.channels.infrastructure.plugin.woocommerce.verify_connection import (
    WooVerifyConnectionPlugin,
)
from src.modules.channels.infrastructure.plugin.woocommerce.read_publication_page import (
    WooReadPublicationPagePlugin,
)


class WooPluginFactory:
    """Собирает реализованные read capabilities WooCommerce."""

    manifest: PluginManifestDTO = MANIFEST

    def validate(
        self, settings: ResourceSettingsDTO, credentials: dict[str, str] | None
    ) -> None:
        """Проверяет настройки и секретную форму без внешних вызовов."""
        pass
        if credentials is not None:
            try:
                WooCredentials.model_validate(credentials)
            except ValidationError:
                raise ChannelsValidationError("invalid_credentials_shape") from None

    def verifier(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> VerifyConnectionPlugin:
        """Создаёт scoped проверку доступа."""
        return WooVerifyConnectionPlugin(credentials, http)

    def reader(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationPagePlugin:
        """Создаёт scoped чтение публикаций."""
        return WooReadPublicationPagePlugin(credentials, http)
