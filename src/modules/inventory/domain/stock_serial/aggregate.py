from dataclasses import dataclass, replace
from typing import Self

from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemTrackingSnapshotError,
)
from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_serial import StockSerialPolicy
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialValueError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)


@dataclass(frozen=True, slots=True)
class StockSerial:
    """Идентичность одного серийного экземпляра и необязательная связь с партией."""

    id: StockSerialIdVO
    inventory_item_id: InventoryItemIdVO
    number: SerialNumberVO
    lot_id: StockLotIdVO | None

    @classmethod
    def create(
        cls,
        *,
        identifier: StockSerialIdVO,
        inventory_item: InventoryItemTrackingSnapshot,
        number: SerialNumberVO,
        lot: StockLotSnapshot | None = None,
    ) -> Self:
        """Создаёт экземпляр по текущим настройкам товара и снимку связанной партии."""
        if not isinstance(inventory_item, InventoryItemTrackingSnapshot):
            raise InvalidInventoryItemTrackingSnapshotError(
                "Для создания экземпляра нужен снимок прослеживаемости товара."
            )
        if lot is not None and not isinstance(lot, StockLotSnapshot):
            raise InvalidStockLotSnapshotError(
                "Ожидался снимок партии StockLotSnapshot."
            )
        serial = cls.restore(
            identifier=identifier,
            inventory_item_id=inventory_item.inventory_item_id,
            number=number,
            lot_id=lot.id if lot is not None else None,
        )
        StockSerialPolicy.ensure_compatible(
            inventory_item_id=serial.inventory_item_id,
            inventory_item=inventory_item,
            lot_id=serial.lot_id,
            lot=lot,
        )
        return serial

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockSerialIdVO,
        inventory_item_id: InventoryItemIdVO,
        number: SerialNumberVO,
        lot_id: StockLotIdVO | None,
    ) -> Self:
        """Восстанавливает идентичность и ссылку на партию без текущих настроек товара."""
        serial = cls(identifier, inventory_item_id, number, lot_id)
        serial._validate()
        return serial

    def change_identification(
        self,
        number: SerialNumberVO,
        *,
        inventory_item: InventoryItemTrackingSnapshot,
        lot: StockLotSnapshot | None,
    ) -> Self:
        """Атомарно исправляет номер и партию, сохраняя ID и SKU до начала складского учёта."""
        self._validate()
        if lot is not None and not isinstance(lot, StockLotSnapshot):
            raise InvalidStockLotSnapshotError(
                "Ожидался снимок партии StockLotSnapshot."
            )
        candidate = replace(
            self, number=number, lot_id=lot.id if lot is not None else None
        )
        candidate._validate()
        StockSerialPolicy.ensure_compatible(
            inventory_item_id=self.inventory_item_id,
            inventory_item=inventory_item,
            lot_id=candidate.lot_id,
            lot=lot,
        )
        return self if candidate == self else candidate

    def snapshot(self) -> StockSerialSnapshot:
        """Возвращает проверенную идентичность и связь с партией без передачи корня."""
        self._validate()
        return StockSerialSnapshot(self.id, self.inventory_item_id, self.lot_id)

    def _validate(self) -> None:
        """Проверяет собственные типы идентификаторов, номера и ссылки на партию."""
        if (
            not isinstance(self.id, StockSerialIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.number, SerialNumberVO)
            or (self.lot_id is not None and not isinstance(self.lot_id, StockLotIdVO))
        ):
            raise InvalidStockSerialValueError(
                "Нужны типизированные ID, серийный номер и ссылка на партию."
            )
