from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountResultError,
)
from src.modules.inventory.domain.inventory_count.sheet_source_snapshot import (
    InventoryCountSheetSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.result_ref import (
    InventoryCountResultRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class InventoryCountAdjustmentSourceSnapshot:
    """Передаёт состояние родителя и обе ссылки для построения корректировки без передачи агрегата."""

    id: InventoryCountIdVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    scope: CountScopeVO
    status: InventoryCountStatus
    baseline: InventoryCountBaselineRefVO | None
    result: InventoryCountResultRefVO | None
    updated_at: datetime
    version: int

    def ensure_valid(self) -> None:
        """Проверяет типы, ссылки и UTC-хронологию, не подменяя версию родителя версией результата."""
        InventoryCountSheetSourceSnapshot(
            self.id,
            self.warehouse_id,
            self.owner_id,
            self.scope,
            self.status,
            self.baseline,
            self.updated_at,
            self.version,
        ).ensure_valid()
        if (self.status is InventoryCountStatus.COUNTED) != (
            self.result is not None
        ) or (
            self.result is not None
            and not isinstance(self.result, InventoryCountResultRefVO)
        ):
            raise InvalidInventoryCountResultError(
                "Ссылка на результат обязательна только в COUNTED."
            )
        if self.result is not None:
            self.result.ensure_valid()
            if (
                not self.baseline.snapshot_at
                <= self.result.prepared_at
                <= self.updated_at
            ):
                raise InvalidInventoryCountResultError(
                    "Результат должен находиться между основанием и текущим состоянием родителя."
                )
