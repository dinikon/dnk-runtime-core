from src.modules.price_lists.application.price_list.use_case.dependencies import (
    PriceListUseCase,
)
from src.modules.price_lists.application.price_list.dto.action_dto import ActionDTO
from src.modules.price_lists.application.price_list.command.restore_price_list_command import (
    RestorePriceListCommand,
)


class RestorePriceListUseCase(PriceListUseCase):
    """Выполняет действие restore_price_list через внедрённые порты."""

    async def __call__(self, command: RestorePriceListCommand) -> ActionDTO:
        """Выполняет сценарий через внедрённые доменные порты."""
        price = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        now = self.clock.now()
        price.transition("restore", command.actor_id, now)
        job_id = None
        canceled = None
        await self.repository.save(command.tenant_id, price)
        return ActionDTO(status=price.status, job_id=job_id)


__all__ = ["RestorePriceListUseCase"]
