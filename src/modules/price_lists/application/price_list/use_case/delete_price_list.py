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
from src.modules.price_lists.application.price_list.command.delete_price_list_command import (
    DeletePriceListCommand,
)


class DeletePriceListUseCase(PriceListUseCase):
    """Выполняет действие delete_price_list через внедрённые порты."""

    async def __call__(self, command: DeletePriceListCommand) -> ActionDTO:
        price = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        if price.status != "archived":
            raise PriceListStateConflict("Archive the price list before deleting it.")
        if command.confirmation_title != price.title:
            raise PriceListValidationError("Confirmation title does not match.")
        await self.jobs.cancel(
            command.tenant_id, price.id, self.clock.now(), delete=True
        )
        await self.repository.delete(command.tenant_id, price.id)
        return ActionDTO()


__all__ = ["DeletePriceListUseCase"]
