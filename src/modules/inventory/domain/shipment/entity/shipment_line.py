from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    QuantityConversionMismatchError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.shipment_line import ShipmentLinePolicy
from src.modules.inventory.domain.shipment.error import InvalidShipmentLineError
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationShipmentSnapshotError,
)
from src.modules.inventory.domain.stock_reservation.shipment_snapshot import (
    StockReservationShipmentSnapshot,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class ShipmentLine:
    """Дочерний план количества под конкретное удержание без фактического исполнения."""

    id: ShipmentLineIdVO
    source_ref: ReservationSourceVO
    reservation_id: StockReservationIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    planned_qty: QuantityVO
    conversion: QuantityConversionSnapshotVO

    @classmethod
    def create(
        cls,
        *,
        identifier: ShipmentLineIdVO,
        inventory_item: InventoryItemStockSnapshot,
        reservation: StockReservationShipmentSnapshot,
        quantity: QuantityVO,
        uom: UomCodeVO,
    ) -> Self:
        """Выводит привязку из снимка резерва и точно пересчитывает ввод в его базовую единицу."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок товара строки."
            )
        inventory_item.ensure_valid()
        if not isinstance(reservation, StockReservationShipmentSnapshot):
            raise InvalidStockReservationShipmentSnapshotError(
                "Нужен снимок удержания для строки отгрузки."
            )
        reservation.ensure_valid()
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=reservation.base_uom
        )
        line = cls.restore(
            identifier=identifier,
            source_ref=reservation.source_ref,
            reservation_id=reservation.id,
            inventory_item_id=reservation.key.inventory_item_id,
            base_uom=reservation.base_uom,
            planned_qty=conversion.to_base_quantity(),
            conversion=conversion,
        )
        line.ensure_compatible(inventory_item=inventory_item, reservation=reservation)
        return line

    @classmethod
    def restore(
        cls,
        *,
        identifier: ShipmentLineIdVO,
        source_ref: ReservationSourceVO,
        reservation_id: StockReservationIdVO,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
    ) -> Self:
        """Восстанавливает исторический план и исходный коэффициент без текущих снимков."""
        line = cls(
            identifier,
            source_ref,
            reservation_id,
            inventory_item_id,
            base_uom,
            planned_qty,
            conversion,
        )
        line.ensure_valid()
        return line

    def ensure_valid(self) -> None:
        """Проверяет собственные ссылки, положительный план и сохранённое равенство пересчёта."""
        if (
            not isinstance(self.id, ShipmentLineIdVO)
            or not isinstance(self.source_ref, ReservationSourceVO)
            or not isinstance(self.reservation_id, StockReservationIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.planned_qty, QuantityVO)
            or self.planned_qty.value.is_zero()
            or not isinstance(self.conversion, QuantityConversionSnapshotVO)
        ):
            raise InvalidShipmentLineError(
                "Нужна типизированная строка с положительным плановым количеством."
            )
        if (
            get_uom(self.base_uom).dimension
            is not get_uom(self.conversion.uom).dimension
        ):
            raise IncompatibleUomError(
                "Исходная и базовая единицы строки должны иметь одну размерность."
            )
        if self.conversion.to_base_quantity() != self.planned_qty:
            raise QuantityConversionMismatchError(
                "Плановое количество не равно сохранённому пересчёту строки."
            )

    def ensure_compatible(
        self,
        *,
        inventory_item: InventoryItemStockSnapshot,
        reservation: StockReservationShipmentSnapshot,
    ) -> None:
        """Повторно проверяет собственные значения и актуальные ограничения товара и удержания."""
        self.ensure_valid()
        ShipmentLinePolicy.ensure_item_compatible(
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            planned_qty=self.planned_qty,
            conversion=self.conversion,
            inventory_item=inventory_item,
        )
        ShipmentLinePolicy.ensure_reservation_compatible(
            reservation_id=self.reservation_id,
            source_ref=self.source_ref,
            inventory_item_id=self.inventory_item_id,
            base_uom=self.base_uom,
            planned_qty=self.planned_qty,
            reservation=reservation,
        )
