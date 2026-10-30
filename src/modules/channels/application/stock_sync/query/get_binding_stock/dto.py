from src.modules.channels.domain.stock_sync.state import DesiredStockVO
from dataclasses import dataclass
from uuid import UUID

from src.modules.channels.application.stock_sync.ports import StockSyncRow


@dataclass(frozen=True, slots=True)
class BindingStockItemDTO:
    """Сравнение количества Catalog и последнего наблюдения площадки."""

    publication_id: UUID
    stock_owner_id: UUID
    catalog_position_id: UUID
    catalog_owner_id: UUID
    catalog_quantity: int | None
    publication_quantity: str | None
    publication_availability: str | None
    export_blocker: str | None
    operation: StockSyncRow | None
    desired_state: DesiredStockVO


@dataclass(frozen=True, slots=True)
class GetBindingStockResultDTO:
    """Публичное состояние количественной синхронизации существующей группы."""

    allow_stock_export: bool
    items: tuple[BindingStockItemDTO, ...]
    warnings: tuple[str, ...] = ()
