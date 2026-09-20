from src.modules.price_lists.application.price_list.use_case.dependencies import (
    PriceListUseCase,
)
from src.modules.price_lists.application.price_list.dto.action_dto import ActionDTO
from src.modules.price_lists.domain.price_list.error import PriceListStateConflict
from src.modules.price_lists.application.price_list.command.save_mapping_command import (
    SaveMappingCommand,
)


class SaveMappingUseCase(PriceListUseCase):
    """Выполняет действие save_mapping через внедрённые порты."""

    async def __call__(self, command: SaveMappingCommand) -> ActionDTO:
        """Выполняет сценарий через внедрённые доменные порты."""
        price = await self.repository.get(command.tenant_id, command.price_list_id)
        price.require_editable()
        candidate = self.preview.candidate(
            price,
            dict(
                source_config=command.source_config,
                mapping_config=command.mapping_config,
            ),
        )
        await self.preview.inspect(candidate, limit=50, validate=True)
        current = await self.repository.get(
            command.tenant_id, command.price_list_id, for_update=True
        )
        if (
            current.schedule_revision != price.schedule_revision
            or current.mapping_version != price.mapping_version
        ):
            raise PriceListStateConflict(
                "Price-list settings changed during validation."
            )
        current.configure_mapping(
            command.source_config,
            command.mapping_config,
            command.actor_id,
            self.clock.now(),
        )
        await self.repository.save(command.tenant_id, current)
        return ActionDTO(status="ready")


__all__ = ["SaveMappingUseCase"]
