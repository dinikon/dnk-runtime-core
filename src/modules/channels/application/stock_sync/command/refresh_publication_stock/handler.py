from src.modules.channels.application.stock_sync.command.refresh_publication_stock.command import (
    RefreshPublicationStockCommand,
)
from src.modules.channels.application.stock_sync.command.refresh_publication_stock.dto import (
    RefreshPublicationStockResultDTO,
)
from src.modules.channels.application.stock_sync.service import StockOperations
from src.modules.shared.domain.time.clock_port import ClockPort


class RefreshPublicationStockHandler:
    """Координирует самостоятельный сценарий refresh_publication_stock."""

    def __init__(self, operations: StockOperations, clock: ClockPort) -> None:
        """Получает сервис общего UoW и часы."""
        self.operations, self.clock = operations, clock

    async def execute(
        self, command: RefreshPublicationStockCommand
    ) -> RefreshPublicationStockResultDTO:
        """Возвращает принятые задания без ожидания платформенного API."""
        return RefreshPublicationStockResultDTO(
            await self.operations.request(
                tenant_id=command.tenant_id,
                channel_id=command.channel_id,
                group_id=command.group_id,
                direction="read",
                publication_ids=command.publication_ids,
                now=self.clock.now(),
            )
        )
