from src.modules.channels.infrastructure.plugin.prom.batch_export import (
    PromBatchExportPlugin,
)
from src.modules.channels.application.batch_export.plugin_contract import (
    BatchExportPlugin,
)
from src.modules.channels.application.port.plugin_services import (
    PluginBatchHttpTransport,
)
from src.modules.channels.infrastructure.plugin.prom.update_content import (
    PromContentUpdatePlugin,
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
from src.modules.channels.infrastructure.plugin.prom.read_publication_details import (
    PromReadPublicationDetailsPlugin,
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
from src.modules.channels.infrastructure.plugin.prom.manifest import (
    MANIFEST,
    PromCredentials,
    PromSettings,
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
    ) -> ConnectionSettingsReferencesDTO:
        """Проверяет настройки и секретную форму без внешних вызовов."""
        if settings.endpoint != "https://my.prom.ua":
            raise ChannelsValidationError("prom_endpoint_must_be_my_prom_ua")
        try:
            parsed = PromSettings.model_validate(settings.options)
        except ValidationError:
            raise ChannelsValidationError("invalid_settings_shape") from None
        if credentials is not None:
            try:
                PromCredentials.model_validate(credentials)
            except ValidationError:
                raise ChannelsValidationError("invalid_credentials_shape") from None

        return ConnectionSettingsReferencesDTO(
            tuple(parsed.locales), (parsed.currency,)
        )

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

    def detail_reader(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> ReadPublicationDetailsPlugin:
        """Создаёт scoped полное чтение карточки."""
        return PromReadPublicationDetailsPlugin(credentials, http)

    def content_updater(
        self, credentials: PluginCredentialsAccess, http: PluginContentHttpTransport
    ) -> ContentUpdatePlugin:
        """Собирает scoped capability контентного обновления."""
        return PromContentUpdatePlugin(credentials, http)

    def batch_exporter(
        self, credentials: PluginCredentialsAccess, http: PluginBatchHttpTransport
    ) -> BatchExportPlugin:
        """Собирает XML-экспорт на публичных scoped фасадах."""
        return PromBatchExportPlugin(credentials, http)
