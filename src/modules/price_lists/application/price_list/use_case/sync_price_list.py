from src.modules.price_lists.application.price_list.use_case.dependencies import (
    PriceListUseCase,
)
from src.modules.price_lists.application.price_list.dto.action_dto import ActionDTO
from src.modules.price_lists.domain.price_list.error import PriceListStateConflict
from src.modules.price_lists.application.price_list.command.sync_price_list_command import (
    SyncPriceListCommand,
)


class SyncPriceListUseCase(PriceListUseCase):
    """Выполняет действие sync_price_list через внедрённые порты."""

    async def __call__(self, command: SyncPriceListCommand) -> ActionDTO:
        """Выполняет сценарий через внедрённые доменные порты."""
        price = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        if price.status != "active":
            raise PriceListStateConflict("Only active price lists can be synchronized.")
        job_id = await self.jobs.schedule_sync(
            command.tenant_id,
            price.id,
            price.schedule_revision,
            self.clock.now(),
            "manual",
            job_id=self.identifiers.new(),
        )
        return ActionDTO(status="queued", job_id=job_id)


__all__ = ["SyncPriceListUseCase"]
