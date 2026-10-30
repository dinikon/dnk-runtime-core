from src.modules.channels.domain.stock_sync.error import StockSyncError
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
        operation_ids = await self.operations.request(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            direction="write",
            publication_ids=(),
            now=self.clock.now(),
        )
        plans = await self.operations.planning.connection_items(
            (await self.operations.planning.bindings.connection(command.channel_id)).id,
            self.clock.now(),
        )
        warnings = []
        for plan in plans:
            if plan.group.id != command.group_id:
                continue
            try:
                self.operations.planning.ensure_exportable(plan, plans)
            except StockSyncError as exc:
                warnings.append(exc.code)
        return ExportCatalogStockResultDTO(
            operation_ids, tuple(dict.fromkeys(warnings))
        )
