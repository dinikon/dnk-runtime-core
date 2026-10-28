from src.modules.channels.application.catalog_binding.command.update_catalog_binding.command import (
    UpdateCatalogBindingCommand,
)
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.command.update_catalog_binding.dto import (
    UpdateCatalogBindingResultDTO,
)


class UpdateCatalogBindingHandler:
    """Сценарий update_catalog_binding на портах внешнего UoW."""

    def __init__(self, writes: BindingWrites, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.writes, self.clock = writes, clock

    async def execute(
        self, command: UpdateCatalogBindingCommand
    ) -> UpdateCatalogBindingResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        group = await self.writes.update(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            expected_revision=command.expected_revision,
            items=command.items,
            catalog_token=command.catalog_token,
            publication_token=command.publication_token,
            actor_id=command.actor_id,
            locale=command.locale,
            now=self.clock.now(),
        )
        return UpdateCatalogBindingResultDTO(group.id.uuid, group.revision)
