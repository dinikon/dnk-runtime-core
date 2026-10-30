from dataclasses import dataclass

from src.modules.channels.application.stock_sync.work import StockWorkSnapshot


@dataclass(frozen=True, slots=True)
class PrepareStockSyncResultDTO:
    """Отсутствующий снимок означает устаревшее либо завершённое задание."""

    snapshot: StockWorkSnapshot | None
