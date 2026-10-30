from src.modules.channels.application.content_delivery.command.apply_content_reconciliation.command import (
    ApplyContentReconciliationCommand,
)
from src.modules.channels.application.content_delivery.command.apply_content_reconciliation.dto import (
    ApplyContentReconciliationResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError


class ApplyContentReconciliationHandler:
    """Фиксирует только подтверждение чтением; несовпадение не разрешает повтор PUT."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Использует ту же атомарную фиксацию цели и media в общем UoW."""
        self._service = service

    async def execute(
        self, command: ApplyContentReconciliationCommand
    ) -> ApplyContentReconciliationResultDTO:
        """Не подменяет результат записи результатом другого сценария."""
        if not command.snapshot.reconcile:
            raise ContentDeliveryError(
                "content_reconciliation_unavailable", conflict=True
            )
        applied = await self._service.apply(
            tenant_id=command.tenant_id,
            snapshot=command.snapshot,
            lock_token=command.lock_token,
            result=command.result,
        )
        return ApplyContentReconciliationResultDTO(applied)
