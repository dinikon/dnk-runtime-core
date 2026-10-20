from src.modules.channels.application.content_update.plugin_contract import (
    InspectContentUpdateInputDTO,
    InspectContentUpdateOutcomeDTO,
    SendContentUpdateInputDTO,
    SendContentUpdateOutcomeDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.infrastructure.plugin.prom.read_publication_details import (
    PromReadPublicationDetailsPlugin,
)


class PromContentUpdatePlugin:
    """Предоставляет сравнение; закрывает XML-запись до подтверждения update-only API."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Переиспользует scoped read фасады существующего плагина."""
        self.credentials, self.http = credentials, http

    async def inspect(
        self, request: InspectContentUpdateInputDTO
    ) -> InspectContentUpdateOutcomeDTO:
        """Читает обе настроенные локали без предположений о параметрах импорта."""
        details = await PromReadPublicationDetailsPlugin(
            self.credentials, self.http
        ).execute(request.target)
        return InspectContentUpdateOutcomeDTO(
            details.translations, ("content_update_update_only_unconfirmed",)
        )

    async def send(
        self, request: SendContentUpdateInputDTO
    ) -> SendContentUpdateOutcomeDTO:
        """Не отправляет импорт, способный создать удалённую или неизвестную карточку."""
        raise PluginCallError("content_update_update_only_unconfirmed")
