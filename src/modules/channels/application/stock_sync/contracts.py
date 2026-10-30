from dataclasses import dataclass

from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class PlatformStockSnapshot:
    """Конкретный результат чтения с нативными полями только об остатке."""

    stock: StockSnapshotVO
    platform_data: JsonObject
