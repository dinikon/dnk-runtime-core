from src.modules.channels.application.content_delivery.command.apply_content_delivery.command import (
    ApplyContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.command.apply_content_delivery.dto import (
    ApplyContentDeliveryResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class ApplyContentDeliveryHandler:
    """Координирует apply_content_delivery в общем внешнем UoW."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Получает сервис с конкретными портами без доступа к SQL."""
        self._service = service

    async def execute(
        self, command: ApplyContentDeliveryCommand
    ) -> ApplyContentDeliveryResultDTO:
        """Передаёт явные параметры и возвращает собственный DTO сценария."""
        result = await self._service.apply(
            tenant_id=command.tenant_id,
            snapshot=command.snapshot,
            lock_token=command.lock_token,
            result=command.result,
        )
        return ApplyContentDeliveryResultDTO(result)
