from src.modules.channels.application.content_delivery.command.authorize_content_delivery.command import (
    AuthorizeContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.command.authorize_content_delivery.dto import (
    AuthorizeContentDeliveryResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class AuthorizeContentDeliveryHandler:
    """Координирует authorize_content_delivery в общем внешнем UoW."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Получает сервис с конкретными портами без доступа к SQL."""
        self._service = service

    async def execute(
        self, command: AuthorizeContentDeliveryCommand
    ) -> AuthorizeContentDeliveryResultDTO:
        """Передаёт явные параметры и возвращает собственный DTO сценария."""
        result = await self._service.accepts_send(
            tenant_id=command.tenant_id,
            snapshot=command.snapshot,
            lock_token=command.lock_token,
        )
        return AuthorizeContentDeliveryResultDTO(result)
