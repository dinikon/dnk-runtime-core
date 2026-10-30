from dataclasses import dataclass
from uuid import UUID

from src.modules.channels.application.stock_sync.command.prepare_stock_sync.command import (
    PrepareStockSyncCommand,
)
from src.modules.channels.application.stock_sync.work import StockWorkSnapshot
from src.modules.channels.application.stock_sync.contracts import PlatformStockSnapshot


@dataclass(frozen=True, slots=True)
class ApplyStockSyncCommand:
    """Ответ одного сетевого шага с fencing исходного снимка."""

    job: PrepareStockSyncCommand
    snapshot: StockWorkSnapshot
    result: PlatformStockSnapshot | None
    owner_id: UUID | None
    error_code: str | None
