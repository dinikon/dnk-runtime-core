from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InventoryCountContextMismatchError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_id import (
    InventoryCountBaselineIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class InventoryCountBaselineSnapshot:
    """Неизменяемое учётное основание вне корня с адресами и раздельными версиями физических позиций."""

    id: InventoryCountBaselineIdVO
    inventory_count_id: InventoryCountIdVO
    inventory_count_version: int
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    scope: CountScopeVO
    snapshot_at: datetime
    locations: tuple[StockLocationSnapshot, ...]
    positions: tuple[StockPositionCountingSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет собственный состав, уникальность, принадлежность позиций области и UTC без текущих справочников."""
        if (
            not isinstance(self.id, InventoryCountBaselineIdVO)
            or not isinstance(self.inventory_count_id, InventoryCountIdVO)
            or type(self.inventory_count_version) is not int
            or self.inventory_count_version < 0
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.scope, CountScopeVO)
            or not isinstance(self.locations, tuple)
            or not isinstance(self.positions, tuple)
        ):
            raise InvalidInventoryCountBaselineError(
                "Нужно типизированное полное учётное основание."
            )
        self.scope.ensure_valid()
        normalize_inventory_count_time(self.snapshot_at)
        if self.snapshot_at.utcoffset() != timedelta(0):
            raise InvalidInventoryCountBaselineError(
                "Основание должно хранить время в UTC."
            )
        locations = set()
        for location in self.locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidInventoryCountBaselineError(
                    "Нужны снимки адресов основания."
                )
            location.ensure_valid()
            if location.id in locations:
                raise InvalidInventoryCountBaselineError("Адрес основания повторяется.")
            locations.add(location.id)
            if location.warehouse_id != self.warehouse_id:
                raise InventoryCountContextMismatchError(
                    "Адрес основания относится к другому складу."
                )
        if self.scope.count_type is CountType.PARTIAL and locations != set(
            self.scope.location_ids
        ):
            raise InventoryCountContextMismatchError(
                "Основание должно содержать ровно выбранные адреса."
            )
        identifiers, dimensions = set(), set()
        for position in self.positions:
            if not isinstance(position, StockPositionCountingSnapshot):
                raise InvalidInventoryCountBaselineError(
                    "Нужны снимки количества и версии позиций."
                )
            position.ensure_valid()
            if position.id in identifiers or position.dimensions in dimensions:
                raise InvalidInventoryCountBaselineError(
                    "ID и комбинации измерений позиций не должны повторяться."
                )
            identifiers.add(position.id)
            dimensions.add(position.dimensions)
            if (
                position.dimensions.owner_id != self.owner_id
                or position.dimensions.location_id not in locations
            ):
                raise InventoryCountContextMismatchError(
                    "Позиция не принадлежит владельцу или адресам основания."
                )
