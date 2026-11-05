from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountSheetSourceError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
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
class InventoryCountSheetSourceSnapshot:
    """Передаёт текущую инвентаризацию и ссылку на её основание без коллекции ведомостей."""

    id: InventoryCountIdVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    scope: CountScopeVO
    status: InventoryCountStatus
    baseline: InventoryCountBaselineRefVO | None
    updated_at: datetime
    version: int

    def ensure_valid(self) -> None:
        """Проверяет собственный состав, состояние ссылки, строгую версию и UTC-хронологию."""
        if (
            not isinstance(self.id, InventoryCountIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.scope, CountScopeVO)
            or not isinstance(self.status, InventoryCountStatus)
            or (
                self.baseline is not None
                and not isinstance(self.baseline, InventoryCountBaselineRefVO)
            )
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidInventoryCountSheetSourceError(
                "Нужен типизированный снимок инвентаризации для ведомости."
            )
        self.scope.ensure_valid()
        normalize_inventory_count_time(self.updated_at)
        if self.updated_at.utcoffset() != timedelta(0):
            raise InvalidInventoryCountSheetSourceError(
                "Момент снимка должен храниться в UTC."
            )
        if (self.status is InventoryCountStatus.IN_PROGRESS) != (
            self.baseline is not None
        ):
            raise InvalidInventoryCountSheetSourceError(
                "Ссылка на основание обязательна только для IN_PROGRESS."
            )
        if self.baseline is not None:
            self.baseline.ensure_valid()
            if self.baseline.snapshot_at > self.updated_at:
                raise InvalidInventoryCountSheetSourceError(
                    "Основание не может быть позже текущего состояния инвентаризации."
                )
