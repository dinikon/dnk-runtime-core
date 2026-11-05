from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.stock_position.availability_snapshot import (
    StockPositionAvailabilitySnapshot,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)

from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.stock_dimensions import StockDimensionsPolicy
from src.modules.inventory.domain.policy.stock_quantity import StockQuantityPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockPositionValueError,
    StockPositionUomMismatchError,
    StockPositionVersionConflictError,
    StockPostingPositionMismatchError,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockLedgerEntrySnapshotError,
)
from src.modules.inventory.domain.stock_posting.ledger_entry_snapshot import (
    StockLedgerEntrySnapshot,
)
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


@dataclass(frozen=True, slots=True)
class StockPosition:
    """Физическое количество в неизменяемых измерениях без истории и резервов."""

    id: StockPositionIdVO
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO
    on_hand_qty: QuantityVO
    version: int

    @classmethod
    def create(
        cls,
        *,
        identifier: StockPositionIdVO,
        dimensions: StockDimensionsVO,
        inventory_item: InventoryItemStockSnapshot,
        location: StockLocationSnapshot,
        warehouse: WarehouseSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> Self:
        """Создаёт нулевую позицию версии 0 по проверенным ссылкам и настройкам товара."""
        StockDimensionsPolicy.ensure_compatible(
            dimensions=dimensions,
            inventory_item=inventory_item,
            location=location,
            warehouse=warehouse,
            lot=lot,
            serial=serial,
        )
        return cls.restore(
            identifier=identifier,
            dimensions=dimensions,
            base_uom=inventory_item.base_uom,
            on_hand_qty=QuantityVO(Decimal(0)),
            version=0,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockPositionIdVO,
        dimensions: StockDimensionsVO,
        base_uom: UomCodeVO,
        on_hand_qty: QuantityVO,
        version: int,
    ) -> Self:
        """Восстанавливает полное собственное состояние без текущих снимков и I/O."""
        position = cls(identifier, dimensions, base_uom, on_hand_qty, version)
        position._validate()
        return position

    def availability_snapshot(self) -> StockPositionAvailabilitySnapshot:
        """Возвращает проверенный физический остаток для расчёта пригодного к резервированию количества."""
        self._validate()
        return StockPositionAvailabilitySnapshot(
            self.id, self.dimensions, self.base_uom, self.on_hand_qty
        )

    def snapshot(self) -> StockPositionSnapshot:
        """Возвращает проверенные неизменяемые атрибуты без остатка и версии."""
        self._validate()
        return StockPositionSnapshot(self.id, self.dimensions, self.base_uom)

    def counting_snapshot(self) -> StockPositionCountingSnapshot:
        """Возвращает проверенные физическое количество и версию для учётного основания инвентаризации."""
        self._validate()
        return StockPositionCountingSnapshot(
            self.id, self.dimensions, self.base_uom, self.on_hand_qty, self.version
        )

    def apply_posting_entry(
        self,
        entry: StockLedgerEntrySnapshot,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        location: StockLocationSnapshot,
        warehouse: WarehouseSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> Self:
        """Проверяет целевую позицию, единицу и ожидаемую версию перед применением записи журнала."""
        self._validate()
        if not isinstance(entry, StockLedgerEntrySnapshot):
            raise InvalidStockLedgerEntrySnapshotError(
                "Нужен снимок записи Ledger, а не Entity или сырая дельта."
            )
        entry.ensure_valid()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidStockPositionValueError(
                "Ожидаемая версия должна быть целым неотрицательным числом без bool."
            )
        if expected_version != self.version:
            raise StockPositionVersionConflictError(
                "Ожидаемая версия не совпадает с текущей версией позиции."
            )
        if entry.position_id != self.id:
            raise StockPostingPositionMismatchError(
                "Запись Ledger предназначена для другой физической позиции."
            )
        if entry.base_uom != self.base_uom:
            raise StockPositionUomMismatchError(
                "Базовая единица записи Ledger не соответствует позиции."
            )
        return self.apply_delta(
            entry.quantity_delta,
            inventory_item=inventory_item,
            location=location,
            warehouse=warehouse,
            lot=lot,
            serial=serial,
        )

    def apply_delta(
        self,
        delta: StockDeltaVO,
        *,
        inventory_item: InventoryItemStockSnapshot,
        location: StockLocationSnapshot,
        warehouse: WarehouseSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> Self:
        """Проверяет контекст и возвращает новый остаток с версией +1 для ненулевой дельты."""
        self._validate()
        StockDimensionsPolicy.ensure_compatible(
            dimensions=self.dimensions,
            inventory_item=inventory_item,
            location=location,
            warehouse=warehouse,
            lot=lot,
            serial=serial,
        )
        if self.base_uom != inventory_item.base_uom:
            raise StockPositionUomMismatchError(
                "Базовая единица позиции не соответствует текущим настройкам товара."
            )
        changed = StockQuantityPolicy.apply_delta(
            quantity=self.on_hand_qty, delta=delta, rules=inventory_item.quantity_rules
        )
        if delta.value.is_zero():
            return self
        position = replace(self, on_hand_qty=changed, version=self.version + 1)
        position._validate()
        return position

    def _validate(self) -> None:
        """Проверяет собственные типы, версию и поштучный остаток конкретной серии."""
        if (
            not isinstance(self.id, StockPositionIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.on_hand_qty, QuantityVO)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockPositionValueError(
                "Нужны типизированные значения позиции и целая неотрицательная версия."
            )
        get_uom(self.base_uom)
        if self.dimensions.serial_id is not None and (
            self.base_uom != UomCodeVO("PCS")
            or self.on_hand_qty.value not in (Decimal(0), Decimal(1))
        ):
            raise InvalidSerialStockQuantityError(
                "Конкретная серия требует PCS и остаток 0 или 1."
            )
