from src.modules.price_lists.application.price_list.use_case.dependencies import (
    PriceListUseCase,
)
from src.modules.price_lists.application.price_list.dto.action_dto import ActionDTO
from src.modules.price_lists.domain.price_list.value_object.configuration import (
    ScheduleVO,
)
from src.modules.price_lists.application.price_list.command.save_schedule_command import (
    SaveScheduleCommand,
)


class SaveScheduleUseCase(PriceListUseCase):
    """Выполняет действие save_schedule через внедрённые порты."""

    async def __call__(self, command: SaveScheduleCommand) -> ActionDTO:
        """Выполняет сценарий через внедрённые доменные порты."""
        price = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        price.require_editable()
        schedule = ScheduleVO(
            command.cron_expression,
            command.timezone,
            command.new_item_policy,
            command.missing_item_policy,
            command.missing_threshold,
        )
        next_at = self.calendar.next(
            schedule.cron_expression, schedule.timezone, after=self.clock.now()
        )
        price.configure_schedule(schedule, next_at, command.actor_id, self.clock.now())
        await self.repository.save(command.tenant_id, price)
        return ActionDTO(next_sync_at=next_at)


__all__ = ["SaveScheduleUseCase"]
