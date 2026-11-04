from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.availability_pool.error import (
    AvailabilityAssessmentDateError,
    AvailabilityPoolContextMismatchError,
    AvailabilityPoolUomMismatchError,
    AvailabilityPoolVersionConflictError,
    ExcessiveReservationReleaseError,
    ExcessiveReservationConsumptionError,
    InsufficientAvailableStockError,
    InvalidAvailabilityPoolValueError,
    InvalidReservationQuantityError,
)
from src.modules.inventory.domain.availability_pool.reservation_snapshot import (
    AvailabilityPoolReservationSnapshot,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.inventory_item.availability_snapshot import (
    InventoryItemAvailabilitySnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemAvailabilitySnapshotError,
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.policy.stock_availability import (
    StockAvailabilityPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.availability_snapshot import (
    StockPositionAvailabilitySnapshot,
)
from src.modules.inventory.domain.stock_serial.availability_snapshot import (
    StockSerialAvailabilitySnapshot,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


@dataclass(frozen=True, slots=True)
class AvailabilityPool:
    """Общий мягкий резерв в неизменяемой области учёта без позиций и коллекции обязательств."""

    id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    base_uom: UomCodeVO
    eligible_qty: QuantityVO
    reserved_qty: QuantityVO
    assessed_on: date
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: AvailabilityPoolIdVO,
        key: AvailabilityPoolKeyVO,
        inventory_item: InventoryItemAvailabilitySnapshot,
        warehouse: WarehouseSnapshot,
        as_of: date,
        positions: tuple[StockPositionAvailabilitySnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialAvailabilitySnapshot, ...] = (),
    ) -> Self:
        """Создаёт пул версии 0 с рассчитанным пригодным запасом и нулевым резервом."""
        if not isinstance(inventory_item, InventoryItemAvailabilitySnapshot):
            raise InvalidInventoryItemAvailabilitySnapshotError(
                "Для создания пула нужен снимок правил доступности товара."
            )
        inventory_item.ensure_valid()
        pool = cls.restore(
            identifier=identifier,
            key=key,
            base_uom=inventory_item.base_uom,
            eligible_qty=QuantityVO(Decimal(0)),
            reserved_qty=QuantityVO(Decimal(0)),
            assessed_on=as_of,
            version=0,
        )
        eligible = pool._assess(
            inventory_item=inventory_item,
            warehouse=warehouse,
            as_of=as_of,
            positions=positions,
            locations=locations,
            lots=lots,
            serials=serials,
        )
        pool = replace(pool, eligible_qty=eligible)
        pool._validate()
        return pool

    @classmethod
    def restore(
        cls,
        *,
        identifier: AvailabilityPoolIdVO,
        key: AvailabilityPoolKeyVO,
        base_uom: UomCodeVO,
        eligible_qty: QuantityVO,
        reserved_qty: QuantityVO,
        assessed_on: date,
        version: int,
    ) -> Self:
        """Восстанавливает собственное историческое состояние, включая дефицит, без текущих снимков."""
        pool = cls(
            identifier, key, base_uom, eligible_qty, reserved_qty, assessed_on, version
        )
        pool._validate()
        return pool

    def reservation_snapshot(self) -> AvailabilityPoolReservationSnapshot:
        """Возвращает проверенную привязку обязательства к пулу без разрешения резервировать запас."""
        self._validate()
        return AvailabilityPoolReservationSnapshot(self.id, self.key, self.base_uom)

    @property
    def available_qty(self) -> QuantityVO:
        """Возвращает свободный пригодный запас, ограничивая результат снизу нулём."""
        self._validate()
        return self._positive_difference(self.eligible_qty, self.reserved_qty)

    @property
    def deficit_qty(self) -> QuantityVO:
        """Возвращает необеспеченную часть существующего резерва без удаления обязательств."""
        self._validate()
        return self._positive_difference(self.reserved_qty, self.eligible_qty)

    def refresh_eligible_quantity(
        self,
        *,
        expected_version: int,
        inventory_item: InventoryItemAvailabilitySnapshot,
        warehouse: WarehouseSnapshot,
        as_of: date,
        positions: tuple[StockPositionAvailabilitySnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialAvailabilitySnapshot, ...] = (),
    ) -> Self:
        """Пересчитывает пригодность по текущим снимкам, сохраняя весь действующий резерв."""
        self._ensure_version(expected_version)
        eligible = self._assess(
            inventory_item=inventory_item,
            warehouse=warehouse,
            as_of=as_of,
            positions=positions,
            locations=locations,
            lots=lots,
            serials=serials,
        )
        if eligible == self.eligible_qty and as_of == self.assessed_on:
            return self
        return self._with_changes(eligible_qty=eligible, assessed_on=as_of)

    def reserve(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        inventory_item: InventoryItemAvailabilitySnapshot,
        warehouse: WarehouseSnapshot,
        as_of: date,
        positions: tuple[StockPositionAvailabilitySnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialAvailabilitySnapshot, ...] = (),
    ) -> Self:
        """Повторно оценивает запас и резервирует всё запрошенное количество либо отклоняет переход."""
        self._ensure_version(expected_version)
        eligible = self._assess(
            inventory_item=inventory_item,
            warehouse=warehouse,
            as_of=as_of,
            positions=positions,
            locations=locations,
            lots=lots,
            serials=serials,
        )
        self._ensure_positive_quantity(quantity, inventory_item.quantity_rules)
        available = self._positive_difference(eligible, self.reserved_qty)
        if quantity.value > available.value:
            raise InsufficientAvailableStockError(
                "Недостаточно пригодного запаса за вычетом действующих резервов."
            )
        return self._with_changes(
            eligible_qty=eligible,
            reserved_qty=QuantityArithmeticPolicy.add(self.reserved_qty, quantity),
            assessed_on=as_of,
        )

    def release(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
    ) -> Self:
        """Освобождает часть общего резерва без требования актуальной пригодности или активности склада."""
        self._ensure_version(expected_version)
        self._ensure_item_compatible(inventory_item)
        self._ensure_positive_quantity(quantity, inventory_item.quantity_rules)
        if quantity.value > self.reserved_qty.value:
            raise ExcessiveReservationReleaseError(
                "Нельзя освободить больше общего действующего резерва."
            )
        return self._with_changes(
            reserved_qty=QuantityArithmeticPolicy.subtract(self.reserved_qty, quantity)
        )

    def consume_reserved(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        inventory_item: InventoryItemAvailabilitySnapshot,
        warehouse: WarehouseSnapshot,
        as_of: date,
        positions: tuple[StockPositionAvailabilitySnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialAvailabilitySnapshot, ...] = (),
    ) -> Self:
        """Уменьшает общий резерв и пересчитывает пригодность по физическим снимкам после расхода."""
        self._ensure_version(expected_version)
        eligible = self._assess(
            inventory_item=inventory_item,
            warehouse=warehouse,
            as_of=as_of,
            positions=positions,
            locations=locations,
            lots=lots,
            serials=serials,
        )
        self._ensure_positive_quantity(quantity, inventory_item.quantity_rules)
        if quantity.value > self.reserved_qty.value:
            raise ExcessiveReservationConsumptionError(
                "Нельзя погасить больше общего действующего резерва."
            )
        return self._with_changes(
            eligible_qty=eligible,
            reserved_qty=QuantityArithmeticPolicy.subtract(self.reserved_qty, quantity),
            assessed_on=as_of,
        )

    def _assess(
        self,
        *,
        inventory_item: InventoryItemAvailabilitySnapshot,
        warehouse: WarehouseSnapshot,
        as_of: date,
        positions: tuple[StockPositionAvailabilitySnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...],
        serials: tuple[StockSerialAvailabilitySnapshot, ...],
    ) -> QuantityVO:
        """Проверяет область, единицу и неубывающую дату перед существующим расчётом пригодности."""
        if type(as_of) is not date or as_of < self.assessed_on:
            raise AvailabilityAssessmentDateError(
                "Нужна календарная date не раньше сохранённого дня оценки."
            )
        if not isinstance(inventory_item, InventoryItemAvailabilitySnapshot):
            raise InvalidInventoryItemAvailabilitySnapshotError(
                "Нужен снимок правил доступности товара пула."
            )
        inventory_item.ensure_valid()
        self._ensure_item_compatible(inventory_item.stock_snapshot())
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада пула.")
        warehouse.ensure_valid()
        if warehouse.id != self.key.warehouse_id:
            raise AvailabilityPoolContextMismatchError(
                "Снимок склада не соответствует ключу пула."
            )
        return StockAvailabilityPolicy.calculate_eligible_quantity(
            inventory_item=inventory_item,
            warehouse=warehouse,
            owner_id=self.key.owner_id,
            as_of=as_of,
            positions=positions,
            locations=locations,
            lots=lots,
            serials=serials,
        )

    def _ensure_item_compatible(
        self, inventory_item: InventoryItemStockSnapshot
    ) -> None:
        """Требует тот же товар, неизменённую единицу и кратность текущего резерва шагу."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок товара пула."
            )
        inventory_item.ensure_valid()
        if inventory_item.inventory_item_id != self.key.inventory_item_id:
            raise AvailabilityPoolContextMismatchError(
                "Снимок относится к другому товару."
            )
        if inventory_item.base_uom != self.base_uom:
            raise AvailabilityPoolUomMismatchError(
                "Базовая единица пула не может быть заменена."
            )
        QuantityValidationPolicy.validate(
            quantity=self.reserved_qty, rules=inventory_item.quantity_rules
        )

    def _ensure_version(self, expected_version: int) -> None:
        """Проверяет собственный состав и строгую ожидаемую версию до расчёта нового состояния."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidAvailabilityPoolValueError(
                "Ожидаемая версия должна быть целым неотрицательным числом без bool."
            )
        if expected_version != self.version:
            raise AvailabilityPoolVersionConflictError(
                "Ожидаемая версия пула устарела или ещё не существует."
            )

    def _with_changes(self, **changes: object) -> Self:
        """Возвращает проверенный новый экземпляр с одной следующей версией."""
        pool = replace(self, **changes, version=self.version + 1)
        pool._validate()
        return pool

    def _validate(self) -> None:
        """Проверяет собственные типы, известную единицу, дату и версию, допуская дефицит."""
        if (
            not isinstance(self.id, AvailabilityPoolIdVO)
            or not isinstance(self.key, AvailabilityPoolKeyVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.eligible_qty, QuantityVO)
            or not isinstance(self.reserved_qty, QuantityVO)
            or type(self.assessed_on) is not date
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidAvailabilityPoolValueError(
                "Нужны типизированные значения пула, календарная дата и целая неотрицательная версия."
            )
        get_uom(self.base_uom)

    @staticmethod
    def _ensure_positive_quantity(quantity: QuantityVO, rules: QuantityRulesVO) -> None:
        """Требует типизированное строго положительное количество, кратное шагу товара."""
        QuantityValidationPolicy.validate(quantity=quantity, rules=rules)
        if quantity.value.is_zero():
            raise InvalidReservationQuantityError(
                "Резервируемое или освобождаемое количество должно быть положительным."
            )

    @staticmethod
    def _positive_difference(left: QuantityVO, right: QuantityVO) -> QuantityVO:
        """Возвращает точную разность с нижней границей ноль без отрицательного QuantityVO."""
        if left.value <= right.value:
            return QuantityVO(Decimal(0))
        return QuantityArithmeticPolicy.subtract(left, right)
