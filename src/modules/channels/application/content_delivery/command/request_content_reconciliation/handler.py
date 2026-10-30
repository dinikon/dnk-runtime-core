from src.modules.channels.application.content_delivery.command.request_content_reconciliation.command import (
    RequestContentReconciliationCommand,
)
from src.modules.channels.application.content_delivery.command.request_content_reconciliation.dto import (
    RequestContentReconciliationResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class RequestContentReconciliationHandler:
    """Координирует request_content_reconciliation в общем внешнем UoW."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Получает сервис с конкретными портами без доступа к SQL."""
        self._service = service

    async def execute(
        self, command: RequestContentReconciliationCommand
    ) -> RequestContentReconciliationResultDTO:
        """Передаёт явные параметры и возвращает собственный DTO сценария."""
        result = await self._service.reconcile(
            tenant_id=command.tenant_id,
            actor_id=command.actor_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            publication_id=command.publication_id,
            expected_revision=command.expected_revision,
        )
        return RequestContentReconciliationResultDTO(result)
