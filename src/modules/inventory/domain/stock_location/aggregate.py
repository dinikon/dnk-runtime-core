from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.policy.default_storage_location import (
    DefaultStorageLocationPolicy,
)
from src.modules.inventory.domain.policy.location_availability import (
    LocationAvailabilityPolicy,
)
from src.modules.inventory.domain.policy.location_placement import (
    LocationPlacementPolicy,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidLocationHierarchyError,
    InvalidStockLocationValueError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockLocation:
    """Самостоятельный адрес с фиксированными складом, родителем и назначением без остатков."""

    id: StockLocationIdVO
    warehouse_id: WarehouseIdVO
    parent_location_id: StockLocationIdVO | None
    code: LocationCodeVO
    name: LocationNameVO
    location_type: LocationType
    is_active: bool

    @classmethod
    def create(
        cls,
        *,
        identifier: StockLocationIdVO,
        warehouse: WarehouseSnapshot,
        code: LocationCodeVO,
        name: LocationNameVO,
        location_type: LocationType,
        parent: StockLocationSnapshot | None = None,
    ) -> Self:
        """Создаёт активную локацию по снимкам активного склада и необязательного родителя."""
        LocationPlacementPolicy.ensure_allowed(
            location_id=identifier, warehouse=warehouse, parent=parent
        )
        return cls.restore(
            identifier=identifier,
            warehouse_id=warehouse.id,
            parent_location_id=parent.id if parent is not None else None,
            code=code,
            name=name,
            location_type=location_type,
            is_active=True,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockLocationIdVO,
        warehouse_id: WarehouseIdVO,
        parent_location_id: StockLocationIdVO | None,
        code: LocationCodeVO,
        name: LocationNameVO,
        location_type: LocationType,
        is_active: bool,
    ) -> Self:
        """Восстанавливает собственный состав без загрузки склада и цепочки родителей."""
        location = cls(
            identifier,
            warehouse_id,
            parent_location_id,
            code,
            name,
            location_type,
            is_active,
        )
        location._validate()
        return location

    def snapshot(self) -> StockLocationSnapshot:
        """Возвращает идентичность, принадлежность, назначение и локальную активность."""
        self._validate()
        return StockLocationSnapshot(
            self.id, self.warehouse_id, self.location_type, self.is_active
        )

    def rename(self, name: LocationNameVO) -> Self:
        """Возвращает локацию с новым названием, сохраняя её идентичность и иерархию."""
        return self._with_changes(name=name)

    def change_code(self, code: LocationCodeVO) -> Self:
        """Возвращает локацию с новым каноническим кодом внутри прежнего склада."""
        return self._with_changes(code=code)

    def activate(self) -> Self:
        """Идемпотентно включает локальную активность без каскада по иерархии."""
        return self._with_changes(is_active=True)

    def deactivate(self, *, warehouse: WarehouseSnapshot) -> Self:
        """Локально блокирует адрес после проверки ссылки на основную локацию склада."""
        DefaultStorageLocationPolicy.ensure_can_deactivate(
            location=self.snapshot(), warehouse=warehouse
        )
        return self._with_changes(is_active=False)

    def ensure_available(self, *, warehouse: WarehouseSnapshot) -> None:
        """Проверяет административную доступность текущей локации и её склада."""
        LocationAvailabilityPolicy.ensure_available(
            location=self.snapshot(), warehouse=warehouse
        )

    def _with_changes(self, **changes: object) -> Self:
        """Проверяет новый экземпляр целиком, сохраняя исходный адрес при отказе."""
        location = replace(self, **changes)
        location._validate()
        return location

    def _validate(self) -> None:
        """Проверяет собственные типы, локальную активность и отсутствие прямой самоссылки."""
        if (
            not isinstance(self.id, StockLocationIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or (
                self.parent_location_id is not None
                and not isinstance(self.parent_location_id, StockLocationIdVO)
            )
            or not isinstance(self.code, LocationCodeVO)
            or not isinstance(self.name, LocationNameVO)
            or not isinstance(self.location_type, LocationType)
            or type(self.is_active) is not bool
        ):
            raise InvalidStockLocationValueError(
                "Нужны типизированные значения локации и bool активности."
            )
        if self.parent_location_id == self.id:
            raise InvalidLocationHierarchyError(
                "Локация не может быть своим родителем."
            )
