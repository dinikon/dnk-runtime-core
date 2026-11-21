from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.error import QuantityConversionMismatchError
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentLineError,
    ShipmentItemMismatchError,
    ShipmentReservationMismatchError,
    ShipmentReservationQuantityExceededError,
    ShipmentReservationUnavailableError,
    ShipmentTimeError,
    ShipmentUomMismatchError,
)
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
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentLinePolicy:
    """Проверяет план строки по текущему товару и удержанию без изменения других агрегатов."""

    @staticmethod
    def ensure_item_compatible(
        *,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
        inventory_item: InventoryItemStockSnapshot,
    ) -> None:
        """Требует тот же товар, прежнюю единицу, системный пересчёт и текущий шаг количества."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок товара строки отгрузки."
            )
        inventory_item.ensure_valid()
        if (
            not isinstance(inventory_item_id, InventoryItemIdVO)
            or not isinstance(base_uom, UomCodeVO)
            or not isinstance(planned_qty, QuantityVO)
            or planned_qty.value.is_zero()
            or not isinstance(conversion, QuantityConversionSnapshotVO)
        ):
            raise InvalidShipmentLineError(
                "Нужны типизированные значения положительной строки отгрузки."
            )
        if inventory_item_id != inventory_item.inventory_item_id:
            raise ShipmentItemMismatchError(
                "Снимок товара не соответствует строке отгрузки."
            )
        if base_uom != inventory_item.base_uom:
            raise ShipmentUomMismatchError(
                "Базовую единицу исторической строки нельзя переинтерпретировать."
            )
        expected = UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(1)), from_uom=conversion.uom, to_uom=base_uom
        )
        if (
            conversion.factor_to_base != expected.value
            or conversion.to_base_quantity() != planned_qty
        ):
            raise QuantityConversionMismatchError(
                "План строки не соответствует текущему системному пересчёту."
            )
        QuantityValidationPolicy.validate(
            quantity=planned_qty, rules=inventory_item.quantity_rules
        )

    @staticmethod
    def ensure_reservation_compatible(
        *,
        reservation_id: StockReservationIdVO,
        source_ref: ReservationSourceVO,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        planned_qty: QuantityVO,
        reservation: StockReservationShipmentSnapshot,
    ) -> None:
        """Сверяет неизменяемую привязку и ограничивает план текущим удержанием данного резерва."""
        if not isinstance(reservation, StockReservationShipmentSnapshot):
            raise InvalidStockReservationShipmentSnapshotError(
                "Нужен снимок резерва для плана отгрузки."
            )
        reservation.ensure_valid()
        if (
            not isinstance(reservation_id, StockReservationIdVO)
            or not isinstance(source_ref, ReservationSourceVO)
            or not isinstance(inventory_item_id, InventoryItemIdVO)
            or not isinstance(base_uom, UomCodeVO)
            or not isinstance(planned_qty, QuantityVO)
            or planned_qty.value.is_zero()
        ):
            raise InvalidShipmentLineError(
                "Нужны типизированные значения привязки строки к резерву."
            )
        if (
            reservation_id != reservation.id
            or source_ref != reservation.source_ref
            or inventory_item_id != reservation.key.inventory_item_id
        ):
            raise ShipmentReservationMismatchError(
                "Резерв, основание или товар не соответствуют строке."
            )
        if base_uom != reservation.base_uom:
            raise ShipmentUomMismatchError(
                "Базовая единица резерва не соответствует строке."
            )
        if reservation.status.is_terminal or reservation.reserved_qty.value.is_zero():
            raise ShipmentReservationUnavailableError(
                "Для планирования нужно открытое ненулевое удержание."
            )
        if planned_qty.value > reservation.reserved_qty.value:
            raise ShipmentReservationQuantityExceededError(
                "План превышает текущее удержание резерва."
            )

    @staticmethod
    def ensure_available(
        *,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        as_of: datetime,
        reservation: StockReservationShipmentSnapshot,
    ) -> None:
        """Требует ту же область и пригодное по времени открытое удержание без чтения часов."""
        if not isinstance(reservation, StockReservationShipmentSnapshot):
            raise InvalidStockReservationShipmentSnapshotError(
                "Нужен снимок резерва для отгрузки."
            )
        reservation.ensure_valid()
        if (
            not isinstance(warehouse_id, WarehouseIdVO)
            or not isinstance(owner_id, StockOwnerIdVO)
            or warehouse_id != reservation.key.warehouse_id
            or owner_id != reservation.key.owner_id
        ):
            raise ShipmentReservationMismatchError(
                "Склад и владелец резерва должны соответствовать отгрузке."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < reservation.updated_at
        ):
            raise ShipmentTimeError(
                "Проверка требует UTC-время не раньше текущего снимка резерва."
            )
        if (
            reservation.status.is_terminal
            or reservation.reserved_qty.value.is_zero()
            or (reservation.expires_at is not None and as_of >= reservation.expires_at)
        ):
            raise ShipmentReservationUnavailableError(
                "Удержание закрыто, пусто или его срок уже наступил."
            )
