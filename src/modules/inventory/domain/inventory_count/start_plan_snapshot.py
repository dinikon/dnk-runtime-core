from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountStartPlanError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class InventoryCountStartPlanSnapshot:
    """Передаёт текущую область и версию плана для построения основания без чужого корня."""

    id: InventoryCountIdVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    scope: CountScopeVO
    status: InventoryCountStatus
    updated_at: datetime
    version: int

    def ensure_valid(self) -> None:
        """Проверяет собственные типы, область, строгую версию и UTC-время плана."""
        if (
            not isinstance(self.id, InventoryCountIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.scope, CountScopeVO)
            or not isinstance(self.status, InventoryCountStatus)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidInventoryCountStartPlanError(
                "Нужен типизированный снимок текущего плана запуска."
            )
        self.scope.ensure_valid()
        normalize_inventory_count_time(self.updated_at)
        if self.updated_at.utcoffset() != timedelta(0):
            raise InvalidInventoryCountStartPlanError(
                "Снимок плана должен хранить время в UTC."
            )
