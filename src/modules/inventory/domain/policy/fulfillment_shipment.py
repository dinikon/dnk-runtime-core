from datetime import datetime, timedelta

from src.modules.inventory.domain.fulfillment_plan.value_object.allocation_status import (
    FulfillmentAllocationStatus,
)

from src.modules.inventory.domain.fulfillment_plan.shipment_snapshot import (
    FulfillmentAllocationShipmentSnapshot,
    FulfillmentPlanShipmentSnapshot,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.shipment_confirmation import (
    ShipmentConfirmationPolicy,
)
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.error import (
    InvalidFulfillmentShipmentLineBindingError,
    InvalidShipmentContextError,
    ShipmentFulfillmentMismatchError,
    ShipmentTimeError,
    StaleShipmentFulfillmentSourceError,
)
from src.modules.inventory.domain.shipment.order_snapshot import ShipmentOrderSnapshot
from src.modules.inventory.domain.shipment.value_object.fulfillment_line_binding import (
    FulfillmentShipmentLineBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.fulfillment_source import (
    ShipmentFulfillmentSourceVO,
)
from src.modules.inventory.domain.shipment.value_object.order_ref import (
    ShipmentOrderRefVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.stock_reservation.fulfillment_snapshot import (
    StockReservationFulfillmentSnapshot,
)
from src.modules.inventory.domain.stock_reservation.shipment_snapshot import (
    StockReservationShipmentSnapshot,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class FulfillmentShipmentPolicy:
    """Строит выбранный состав одного Shipment и повторно сверяет его основание без изменения чужих агрегатов."""

    @staticmethod
    def build_lines(
        *,
        fulfillment_plan: FulfillmentPlanShipmentSnapshot,
        warehouse: WarehouseSnapshot,
        order: ShipmentOrderSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        line_bindings: tuple[FulfillmentShipmentLineBindingVO, ...],
        as_of: datetime,
    ) -> tuple[ShipmentLine, ...]:
        """Строит новый черновик по явному непустому набору свободных целых Allocation одного склада."""
        lines = FulfillmentShipmentPolicy._build_lines(
            fulfillment_plan=fulfillment_plan,
            warehouse=warehouse,
            order=order,
            inventory_items=inventory_items,
            reservations=reservations,
            line_bindings=line_bindings,
            as_of=as_of,
        )
        selected_ids = {line.fulfillment_allocation_id for line in lines}
        if any(
            row.id in selected_ids and row.shipment_assignment is not None
            for row in fulfillment_plan.allocations
        ):
            raise ShipmentFulfillmentMismatchError(
                "Выбранная Allocation уже назначена Shipment; новый черновик с ней не создаётся."
            )
        return lines

    @staticmethod
    def _build_lines(
        *,
        fulfillment_plan: FulfillmentPlanShipmentSnapshot,
        warehouse: WarehouseSnapshot,
        order: ShipmentOrderSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        line_bindings: tuple[FulfillmentShipmentLineBindingVO, ...],
        as_of: datetime,
    ) -> tuple[ShipmentLine, ...]:
        """Возвращает одну строку на каждую выбранную целую Allocation с текущими полными удержаниями."""
        if not isinstance(fulfillment_plan, FulfillmentPlanShipmentSnapshot):
            raise InvalidShipmentContextError(
                "Нужно специализированное основание FulfillmentPlan."
            )
        fulfillment_plan.ensure_valid()
        if not isinstance(as_of, datetime) or as_of.utcoffset() != timedelta(0):
            raise ShipmentTimeError("Нужно явное время решения в UTC.")
        if as_of < fulfillment_plan.updated_at:
            raise ShipmentTimeError("Отгрузка не может предшествовать текущему плану.")
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidShipmentContextError("Нужен снимок выбранного склада.")
        ShipmentConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse.id, warehouse=warehouse
        )
        if not isinstance(line_bindings, tuple) or not line_bindings:
            raise InvalidFulfillmentShipmentLineBindingError(
                "Нужен непустой tuple выбора Allocation и ID строк Shipment."
            )
        bindings, ids = {}, set()
        for binding in line_bindings:
            if not isinstance(binding, FulfillmentShipmentLineBindingVO):
                raise InvalidFulfillmentShipmentLineBindingError(
                    "Нужны FulfillmentShipmentLineBindingVO."
                )
            if binding.allocation_id in bindings or binding.shipment_line_id in ids:
                raise InvalidFulfillmentShipmentLineBindingError(
                    "Распределение и ID строки назначаются один раз."
                )
            bindings[binding.allocation_id] = binding.shipment_line_id
            ids.add(binding.shipment_line_id)
        by_id = {row.id: row for row in fulfillment_plan.allocations}
        if not set(bindings) <= set(by_id):
            raise InvalidFulfillmentShipmentLineBindingError(
                "Выбор содержит неизвестную Allocation."
            )
        allocations = tuple(by_id[identifier] for identifier in bindings)
        if any(row.source.warehouse_id != warehouse.id for row in allocations):
            raise InvalidFulfillmentShipmentLineBindingError(
                "Выбранная Allocation относится к другому складу."
            )
        if any(
            row.status is not FulfillmentAllocationStatus.CONFIRMED
            or row.reservation is None
            or row.shipment_progress is not None
            or not row.fulfilled_qty.value.is_zero()
            for row in allocations
        ):
            raise ShipmentFulfillmentMismatchError(
                "Выбранные Allocation должны целиком подтверждаться резервами, относиться к выбранному складу и не иметь исполнения."
            )
        projected = FulfillmentShipmentPolicy._reservation_snapshots(
            owner_id=fulfillment_plan.owner_id,
            allocations=allocations,
            reservations=reservations,
            as_of=as_of,
        )
        if not isinstance(inventory_items, tuple):
            raise InvalidShipmentContextError("Нужен tuple текущих снимков товаров.")
        items = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemStockSnapshot):
                raise InvalidShipmentContextError("Нужны учётные снимки товаров.")
            item.ensure_valid()
            if item.inventory_item_id in items:
                raise InvalidShipmentContextError("Снимок товара повторяется.")
            items[item.inventory_item_id] = item
        if set(items) != {allocation.inventory_item_id for allocation in allocations}:
            raise InvalidShipmentContextError(
                "Нужны ровно товары выбранных Allocation."
            )
        by_reservation = {reservation.id: reservation for reservation in projected}
        lines = tuple(
            ShipmentLine.create(
                identifier=bindings[allocation.id],
                inventory_item=items[allocation.inventory_item_id],
                reservation=by_reservation[allocation.reservation.reservation_id],
                quantity=allocation.quantity,
                uom=allocation.base_uom,
                fulfillment_allocation_id=allocation.id,
            )
            for allocation in sorted(allocations, key=lambda row: row.id.uuid.int)
        )
        ShipmentConfirmationPolicy.ensure_confirmable(
            order_ref=ShipmentOrderRefVO(
                fulfillment_plan.order_ref.system, fulfillment_plan.order_ref.reference
            ),
            warehouse_id=warehouse.id,
            owner_id=fulfillment_plan.owner_id,
            lines=lines,
            warehouse=warehouse,
            order=order,
            inventory_items=inventory_items,
            reservations=projected,
            as_of=as_of,
        )
        return lines

    @staticmethod
    def ensure_confirmable(
        *,
        shipment_id: ShipmentIdVO,
        shipment_version: int,
        source: ShipmentFulfillmentSourceVO,
        order_ref: ShipmentOrderRefVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        lines: tuple[ShipmentLine, ...],
        fulfillment_plan: FulfillmentPlanShipmentSnapshot,
        warehouse: WarehouseSnapshot,
        order: ShipmentOrderSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        as_of: datetime,
    ) -> None:
        """Требует прежнее основание и точный полный состав, повторяя текущие проверки фабрики."""
        if not isinstance(source, ShipmentFulfillmentSourceVO) or not isinstance(
            fulfillment_plan, FulfillmentPlanShipmentSnapshot
        ):
            raise InvalidShipmentContextError(
                "Нужны сохранённая ссылка и текущий снимок плана."
            )
        fulfillment_plan.ensure_valid()
        if (
            source.plan_id != fulfillment_plan.id
            or source.plan_version > fulfillment_plan.version
        ):
            raise StaleShipmentFulfillmentSourceError(
                "Текущий план имеет другой ID либо основание Shipment ссылается на будущую версию."
            )
        if (
            not isinstance(warehouse, WarehouseSnapshot)
            or warehouse.id != warehouse_id
            or owner_id != fulfillment_plan.owner_id
            or order_ref
            != ShipmentOrderRefVO(
                fulfillment_plan.order_ref.system, fulfillment_plan.order_ref.reference
            )
        ):
            raise ShipmentFulfillmentMismatchError(
                "Заказ, владелец или склад отгрузки не соответствуют основанию."
            )
        if not isinstance(lines, tuple) or not lines:
            raise ShipmentFulfillmentMismatchError(
                "Нужен полный непустой состав производной отгрузки."
            )
        for line in lines:
            if not isinstance(line, ShipmentLine):
                raise ShipmentFulfillmentMismatchError("Нужны строки ShipmentLine.")
            line.ensure_valid()
        rebuilt = FulfillmentShipmentPolicy._build_lines(
            fulfillment_plan=fulfillment_plan,
            warehouse=warehouse,
            order=order,
            inventory_items=inventory_items,
            reservations=reservations,
            line_bindings=tuple(
                FulfillmentShipmentLineBindingVO(
                    line.fulfillment_allocation_id, line.id
                )
                for line in lines
            ),
            as_of=as_of,
        )
        if {line.id: line for line in rebuilt} != {line.id: line for line in lines}:
            raise ShipmentFulfillmentMismatchError(
                "Строки отгрузки отличаются от полного состава распределений."
            )
        if (
            not isinstance(shipment_id, ShipmentIdVO)
            or type(shipment_version) is not int
            or shipment_version < 0
        ):
            raise ShipmentFulfillmentMismatchError(
                "Нужны ID и строгая версия подтверждаемого Shipment."
            )
        by_allocation = {row.id: row for row in fulfillment_plan.allocations}
        assigned_ids = {
            row.id
            for row in fulfillment_plan.allocations
            if row.shipment_assignment is not None
            and row.shipment_assignment.shipment_id == shipment_id
        }
        if assigned_ids != {line.fulfillment_allocation_id for line in lines}:
            raise ShipmentFulfillmentMismatchError(
                "Подтверждение требует весь закреплённый состав этого Shipment."
            )
        for line in lines:
            assignment = by_allocation[
                line.fulfillment_allocation_id
            ].shipment_assignment
            if (
                assignment is None
                or (
                    assignment.shipment_id,
                    assignment.shipment_line_id,
                    assignment.shipment_version,
                    assignment.source_plan_version,
                )
                != (shipment_id, line.id, shipment_version, source.plan_version)
                or as_of < assignment.assigned_at
            ):
                raise ShipmentFulfillmentMismatchError(
                    "Подтверждение требует прежнее назначение именно этому Shipment, строке и версии черновика."
                )

    @staticmethod
    def _reservation_snapshots(
        *,
        owner_id: StockOwnerIdVO,
        allocations: tuple[FulfillmentAllocationShipmentSnapshot, ...],
        reservations: tuple[StockReservationFulfillmentSnapshot, ...],
        as_of: datetime,
    ) -> tuple[StockReservationShipmentSnapshot, ...]:
        """Проверяет полные удержания выбранных Allocation и проецирует единый вход в прежний контракт Shipment."""
        if not isinstance(reservations, tuple):
            raise InvalidShipmentContextError(
                "Нужен tuple полных текущих снимков резервов."
            )
        by_id = {}
        for reservation in reservations:
            if not isinstance(reservation, StockReservationFulfillmentSnapshot):
                raise InvalidShipmentContextError(
                    "Нужны StockReservationFulfillmentSnapshot с запросом и погашением."
                )
            reservation.ensure_valid()
            if reservation.id in by_id:
                raise InvalidShipmentContextError("Снимок резерва повторяется.")
            by_id[reservation.id] = reservation
        if set(by_id) != {
            allocation.reservation.reservation_id for allocation in allocations
        }:
            raise InvalidShipmentContextError(
                "Нужны ровно резервы выбранных Allocation без пропусков или лишних."
            )
        result = []
        for allocation in allocations:
            reservation = by_id[allocation.reservation.reservation_id]
            if as_of < reservation.updated_at:
                raise ShipmentTimeError(
                    "Решение не может предшествовать текущему резерву."
                )
            if (
                reservation.version != allocation.reservation.version
                or reservation.status is not StockReservationStatus.RESERVED
                or reservation.key.inventory_item_id != allocation.inventory_item_id
                or reservation.key.warehouse_id != allocation.source.warehouse_id
                or reservation.key.owner_id != owner_id
                or reservation.source_ref != allocation.source_ref
                or reservation.base_uom != allocation.base_uom
                or reservation.requested_qty != allocation.quantity
                or reservation.reserved_qty != allocation.quantity
                or not reservation.consumed_qty.value.is_zero()
                or (
                    reservation.expires_at is not None
                    and as_of >= reservation.expires_at
                )
            ):
                raise ShipmentFulfillmentMismatchError(
                    "Нужен прежний полный непогашенный и неистёкший резерв того же распределения."
                )
            result.append(
                StockReservationShipmentSnapshot(
                    reservation.id,
                    reservation.pool_id,
                    reservation.key,
                    reservation.source_ref,
                    reservation.base_uom,
                    reservation.reserved_qty,
                    reservation.status,
                    reservation.expires_at,
                    reservation.updated_at,
                    reservation.version,
                )
            )
        return tuple(result)
