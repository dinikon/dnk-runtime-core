from src.modules.channels.infrastructure.plugin.woocommerce.update_content import (
    WooContentUpdatePlugin,
)
from src.modules.channels.application.content_update.port.plugin import (
    ContentUpdatePlugin,
)
from src.modules.channels.application.port.plugin_services import (
    PluginContentHttpTransport,
)
from src.modules.channels.application.external_publication.port.read_publication_details_plugin import (
    ReadPublicationDetailsPlugin,
)
from src.modules.channels.infrastructure.plugin.woocommerce.read_publication_details import (
    WooReadPublicationDetailsPlugin,
)
from pydantic import ValidationError
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
from src.modules.channels.domain.error import ChannelsValidationError
from src.modules.channels.infrastructure.plugin.woocommerce.manifest import (
    MANIFEST,
    WooCredentials,
    WooSettings,
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
    ) -> ConnectionSettingsReferencesDTO:
        """Проверяет настройки и секретную форму без внешних вызовов."""
        try:
            parsed = WooSettings.model_validate(settings.options)
        except ValidationError:
            raise ChannelsValidationError("invalid_settings_shape") from None
        if credentials is not None:
            try:
                WooCredentials.model_validate(credentials)
            except ValidationError:
                raise ChannelsValidationError("invalid_credentials_shape") from None

        return ConnectionSettingsReferencesDTO(
            tuple(parsed.locales), (parsed.currency,)
        )

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

    def detail_reader(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationDetailsPlugin:
        """Создаёт scoped полное чтение карточки."""
        return WooReadPublicationDetailsPlugin(credentials, http)

    def content_updater(
        self, credentials: PluginCredentialsAccess, http: PluginContentHttpTransport
    ) -> ContentUpdatePlugin:
        """Собирает scoped capability контентного обновления."""
        return WooContentUpdatePlugin(credentials, http)
