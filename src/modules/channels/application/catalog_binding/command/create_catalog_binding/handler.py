from src.modules.channels.application.catalog_binding.command.create_catalog_binding.command import (
    CreateCatalogBindingCommand,
)
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.command.create_catalog_binding.dto import (
    CreateCatalogBindingResultDTO,
)


class CreateCatalogBindingHandler:
    """Сценарий create_catalog_binding на портах внешнего UoW."""

    def __init__(self, writes: BindingWrites, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.writes, self.clock = writes, clock

    async def execute(
        self, command: CreateCatalogBindingCommand
    ) -> CreateCatalogBindingResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        group = await self.writes.create(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            catalog_root_id=command.catalog_root_id,
            mode=command.mode,
            publication_root_id=command.publication_root_id,
            items=command.items,
            catalog_token=command.catalog_token,
            publication_token=command.publication_token,
            actor_id=command.actor_id,
            locale=command.locale,
            now=self.clock.now(),
        )
        return CreateCatalogBindingResultDTO(group.id.uuid, group.revision)
