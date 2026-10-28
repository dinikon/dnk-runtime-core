from src.modules.channels.application.catalog_binding.command.delete_catalog_binding.command import (
    DeleteCatalogBindingCommand,
)
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.shared.domain.time.clock_port import ClockPort


class DeleteCatalogBindingHandler:
    """Сценарий delete_catalog_binding на портах внешнего UoW."""

    def __init__(self, writes: BindingWrites, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.writes, self.clock = writes, clock

    async def execute(self, command: DeleteCatalogBindingCommand) -> None:
        """Выполняет отдельный сценарий без вложенных handlers."""
        await self.writes.delete(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            expected_revision=command.expected_revision,
        )
