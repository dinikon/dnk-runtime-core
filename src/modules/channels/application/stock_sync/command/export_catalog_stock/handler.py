from src.modules.channels.application.stock_sync.command.export_catalog_stock.command import (
    ExportCatalogStockCommand,
)
from src.modules.channels.application.stock_sync.command.export_catalog_stock.dto import (
    ExportCatalogStockResultDTO,
)
from src.modules.channels.application.stock_sync.service import StockOperations
from src.modules.shared.domain.time.clock_port import ClockPort


class ExportCatalogStockHandler:
    """Координирует самостоятельный сценарий export_catalog_stock."""

    def __init__(self, operations: StockOperations, clock: ClockPort) -> None:
        """Получает сервис общего UoW и часы."""
        self.operations, self.clock = operations, clock

    async def execute(
        self, command: ExportCatalogStockCommand
    ) -> ExportCatalogStockResultDTO:
        """Возвращает принятые задания без ожидания платформенного API."""
        return ExportCatalogStockResultDTO(
            await self.operations.request(
                tenant_id=command.tenant_id,
                channel_id=command.channel_id,
                group_id=command.group_id,
                direction="write",
                publication_ids=command.publication_ids,
                now=self.clock.now(),
            )
        )
