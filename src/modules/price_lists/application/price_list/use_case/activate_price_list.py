from datetime import timedelta
from src.modules.price_lists.application.price_list.use_case.dependencies import (
    PriceListUseCase,
)
from src.modules.price_lists.application.price_list.dto.action_dto import ActionDTO
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.price_list.error import (
    PriceListStateConflict,
    PriceListValidationError,
)
from src.modules.price_lists.domain.price_list.value_object.configuration import (
    TitleVO,
    SourceConfigurationVO,
    MappingConfigurationVO,
    ScheduleVO,
)
from src.modules.price_lists.domain.price_list.value_object.source_url import (
    SourceUrlVO,
    mask_source_url,
)
from src.modules.price_lists.domain.price_list.preset import prom_xml_config
from src.modules.price_lists.application.price_list.command.activate_price_list_command import (
    ActivatePriceListCommand,
)


class ActivatePriceListUseCase(PriceListUseCase):
    """Выполняет действие activate_price_list через внедрённые порты."""

    async def __call__(self, command: ActivatePriceListCommand) -> ActionDTO:
        price = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        now = self.clock.now()
        price.transition("activate", command.actor_id, now)
        job_id = None
        canceled = None
        next_at = self.calendar.next(price.cron_expression, price.timezone, after=now)
        price.update({"next_sync_at": next_at}, command.actor_id, now)
        job_id = await self.jobs.schedule_sync(
            command.tenant_id,
            price.id,
            price.schedule_revision,
            now,
            "initial",
            job_id=self.identifiers.new(),
        )
        await self.jobs.schedule_sync(
            command.tenant_id, price.id, price.schedule_revision, next_at, "cron"
        )
        await self.jobs.schedule_cleanup(
            command.tenant_id,
            (now + timedelta(days=1)).replace(
                hour=3, minute=0, second=0, microsecond=0
            ),
        )
        await self.repository.save(command.tenant_id, price)
        return ActionDTO(status="queued", job_id=job_id)


__all__ = ["ActivatePriceListUseCase"]
