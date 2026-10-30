from src.modules.channels.application.content_delivery.command.prepare_content_delivery.command import (
    PrepareContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.command.prepare_content_delivery.dto import (
    PrepareContentDeliveryResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class PrepareContentDeliveryHandler:
    """Координирует prepare_content_delivery в общем внешнем UoW."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Получает сервис с конкретными портами без доступа к SQL."""
        self._service = service

    async def execute(
        self, command: PrepareContentDeliveryCommand
    ) -> PrepareContentDeliveryResultDTO:
        """Передаёт явные параметры и возвращает собственный DTO сценария."""
        result = await self._service.prepare(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            representation_id=command.representation_id,
            publication_id=command.publication_id,
            job_id=command.job_id,
            lock_token=command.lock_token,
        )
        return PrepareContentDeliveryResultDTO(result)
