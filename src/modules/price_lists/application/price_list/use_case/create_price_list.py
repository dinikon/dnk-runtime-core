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
from src.modules.price_lists.application.price_list.command.create_price_list_command import (
    CreatePriceListCommand,
)


class CreatePriceListUseCase(PriceListUseCase):
    """Выполняет действие create_price_list через внедрённые порты."""

    async def __call__(self, command: CreatePriceListCommand) -> ActionDTO:
        source = command.source_config
        mapping = {}
        SourceUrlVO(command.source_url)
        if command.source_preset == "prom_xml":
            if command.source_format != "xml":
                raise PriceListValidationError("Prom preset requires XML format.")
            preset, mapping = prom_xml_config()
            source = preset | source
        elif command.source_preset is not None:
            raise PriceListValidationError("Unknown source preset.")
        entity = PriceList.create(
            price_list_id=command.price_list_id,
            actor_id=command.actor_id,
            title=command.title,
            source_format=command.source_format,
            source_preset=command.source_preset,
            source_url_secret=self.cipher.encrypt(command.source_url),
            source_url_display=mask_source_url(command.source_url),
            source_config=source,
            mapping_config=mapping,
            now=self.clock.now(),
        )
        await self.repository.add(command.tenant_id, entity)
        return ActionDTO(id=entity.id)


__all__ = ["CreatePriceListUseCase"]
