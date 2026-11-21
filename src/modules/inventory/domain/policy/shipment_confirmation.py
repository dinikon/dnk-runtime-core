from datetime import datetime

from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.shipment_line import ShipmentLinePolicy
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.error import (
    EmptyShipmentError,
    InvalidShipmentContextError,
    InvalidShipmentLineError,
    InvalidShipmentOrderSnapshotError,
    ShipmentLineConflictError,
    ShipmentOrderQuantityExceededError,
    ShipmentOrderUnavailableError,
)
from src.modules.inventory.domain.shipment.order_snapshot import ShipmentOrderSnapshot
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidStockReservationShipmentSnapshotError,
)
from src.modules.inventory.domain.stock_reservation.shipment_snapshot import (
    StockReservationShipmentSnapshot,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentConfirmationPolicy:
    """Подтверждает непустой план по активному складу, заказу и ровно участвующим текущим снимкам."""

    @staticmethod
    def ensure_warehouse(
        *, warehouse_id: WarehouseIdVO, warehouse: WarehouseSnapshot
    ) -> None:
        """Требует типизированный снимок того же активного склада без физических локаций."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада отгрузки.")
        warehouse.ensure_valid()
        if not isinstance(warehouse_id, WarehouseIdVO) or warehouse_id != warehouse.id:
            raise InvalidShipmentContextError(
                "Снимок склада не соответствует отгрузке."
            )
        if not warehouse.is_active:
            raise WarehouseInactiveError(
                "Неактивный склад недоступен для нового или подтверждаемого плана."
            )

    @staticmethod
    def ensure_confirmable(
        *,
        order_ref: ShipmentOrderRefVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        lines: tuple[ShipmentLine, ...],
        warehouse: WarehouseSnapshot,
        order: ShipmentOrderSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        reservations: tuple[StockReservationShipmentSnapshot, ...],
        as_of: datetime,
    ) -> None:
        """Проверяет принадлежность строк заказу и их сумму, не изменяя резервов или заказа."""
        ShipmentConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse_id, warehouse=warehouse
        )
        if not isinstance(order_ref, ShipmentOrderRefVO) or not isinstance(
            owner_id, StockOwnerIdVO
        ):
            raise InvalidShipmentContextError(
                "Нужны типизированные заказ и владелец отгрузки."
            )
        if not isinstance(lines, tuple):
            raise InvalidShipmentLineError("План передаётся в tuple строк.")
        if not lines:
            raise EmptyShipmentError("Нельзя подтвердить пустой план отгрузки.")
        if not isinstance(order, ShipmentOrderSnapshot):
            raise InvalidShipmentOrderSnapshotError("Нужен снимок исходного заказа.")
        order.ensure_valid()
        if order.order_ref != order_ref:
            raise InvalidShipmentContextError("Снимок относится к другому заказу.")
        if not order.is_fulfillable:
            raise ShipmentOrderUnavailableError("Заказ недоступен для исполнения.")
        if not isinstance(inventory_items, tuple) or not isinstance(
            reservations, tuple
        ):
            raise InvalidShipmentContextError(
                "Контекст передаётся в tuple снимков товаров и резервов."
            )
        by_item = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemStockSnapshot):
                raise InvalidInventoryItemStockSnapshotError(
                    "Нужны учётные снимки товаров отгрузки."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InvalidShipmentContextError(
                    "Снимок каждого товара передаётся один раз."
                )
            by_item[item.inventory_item_id] = item
        by_reservation = {}
        for reservation in reservations:
            if not isinstance(reservation, StockReservationShipmentSnapshot):
                raise InvalidStockReservationShipmentSnapshotError(
                    "Нужны снимки текущих удержаний."
                )
            reservation.ensure_valid()
            if reservation.id in by_reservation:
                raise InvalidShipmentContextError(
                    "Снимок каждого резерва передаётся один раз."
                )
            by_reservation[reservation.id] = reservation
        by_source = {line.source_ref: line for line in order.lines}
        ids, used_items, used_reservations = set(), set(), set()
        quantities = {}
        for line in lines:
            if not isinstance(line, ShipmentLine):
                raise InvalidShipmentLineError("Нужны дочерние строки плана отгрузки.")
            line.ensure_valid()
            if line.id in ids or line.reservation_id in used_reservations:
                raise ShipmentLineConflictError(
                    "ID строки и резерв не должны повторяться в отгрузке."
                )
            ids.add(line.id)
            item = by_item.get(line.inventory_item_id)
            reservation = by_reservation.get(line.reservation_id)
            if item is None or reservation is None:
                raise InvalidShipmentContextError(
                    "Отсутствует участвующий снимок товара или резерва."
                )
            used_items.add(line.inventory_item_id)
            used_reservations.add(line.reservation_id)
            line.ensure_compatible(inventory_item=item, reservation=reservation)
            ShipmentLinePolicy.ensure_available(
                warehouse_id=warehouse_id,
                owner_id=owner_id,
                as_of=as_of,
                reservation=reservation,
            )
            source = by_source.get(line.source_ref)
            if (
                source is None
                or source.inventory_item_id != line.inventory_item_id
                or source.base_uom != line.base_uom
            ):
                raise InvalidShipmentContextError(
                    "Строка заказа, товар и базовая единица не соответствуют плану."
                )
            previous = quantities.get(line.source_ref)
            quantities[line.source_ref] = (
                line.planned_qty
                if previous is None
                else QuantityArithmeticPolicy.add(previous, line.planned_qty)
            )
        if used_items != set(by_item) or used_reservations != set(by_reservation):
            raise InvalidShipmentContextError(
                "Лишние снимки товаров и резервов не допускаются."
            )
        for source_ref, quantity in quantities.items():
            if quantity.value > by_source[source_ref].remaining_to_ship_qty.value:
                raise ShipmentOrderQuantityExceededError(
                    "План превышает оставшееся количество строки заказа."
                )
