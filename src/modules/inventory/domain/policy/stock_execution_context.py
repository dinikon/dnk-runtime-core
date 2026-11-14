from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemExecutionSnapshotError,
)
from src.modules.inventory.domain.inventory_item.execution_snapshot import (
    InventoryItemExecutionSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.location_availability import (
    LocationAvailabilityPolicy,
)
from src.modules.inventory.domain.policy.stock_dimensions import StockDimensionsPolicy
from src.modules.inventory.domain.policy.stock_expiration import StockExpirationPolicy
from src.modules.inventory.domain.policy.stock_tracking_dates import (
    StockTrackingDatesPolicy,
)
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionContextError,
)
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.snapshot import (
    StockSerialSnapshot,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockExecutionContextPolicy:
    """Проверяет фактические маршруты по текущим адресам, товарам и карточкам прослеживаемости."""

    @staticmethod
    def ensure_compatible(
        *,
        operation_type: StockOperationType,
        warehouse_id: WarehouseIdVO,
        lines: tuple[StockExecutionLine, ...],
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemExecutionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...],
        serials: tuple[StockSerialSnapshot, ...],
    ) -> None:
        """Требует ровно участвующие снимки, активные адреса и обязательную дату поступления."""
        if not isinstance(operation_type, StockOperationType) or not isinstance(
            warehouse_id, WarehouseIdVO
        ):
            raise InvalidStockExecutionContextError(
                "Нужны типизированные вид операции и склад исполнения."
            )
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада исполнения.")
        warehouse.ensure_valid()
        if warehouse.id != warehouse_id:
            raise InvalidStockExecutionContextError(
                "Склад снимка не соответствует исполнению."
            )
        if (
            not isinstance(lines, tuple)
            or not lines
            or not all(isinstance(line, StockExecutionLine) for line in lines)
        ):
            raise InvalidStockExecutionContextError(
                "Нужны непустые типизированные строки исполнения."
            )
        if not all(
            isinstance(values, tuple)
            for values in (inventory_items, locations, lots, serials)
        ):
            raise InvalidStockExecutionContextError(
                "Контекст исполнения передаётся в tuple снимков."
            )
        by_item = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemExecutionSnapshot):
                raise InvalidInventoryItemExecutionSnapshotError(
                    "Нужны снимки правил исполнения товара."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InvalidStockExecutionContextError(
                    "Снимок каждого товара передаётся один раз."
                )
            by_item[item.inventory_item_id] = item
        by_location = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockLocationSnapshotError(
                    "Нужны снимки фактических локаций."
                )
            location.ensure_valid()
            if location.id in by_location:
                raise InvalidStockExecutionContextError(
                    "Снимок каждой локации передаётся один раз."
                )
            by_location[location.id] = location
        by_lot = {}
        for lot in lots:
            if (
                not isinstance(lot, StockLotSnapshot)
                or not isinstance(lot.id, StockLotIdVO)
                or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
                or not isinstance(lot.dates, StockDatesVO)
            ):
                raise InvalidStockLotSnapshotError(
                    "Нужны типизированные снимки партий с датами."
                )
            if lot.id in by_lot:
                raise InvalidStockExecutionContextError(
                    "Снимок каждой партии передаётся один раз."
                )
            by_lot[lot.id] = lot
        by_serial = {}
        for serial in serials:
            if not isinstance(serial, StockSerialSnapshot):
                raise InvalidStockSerialSnapshotError(
                    "Нужны снимки идентичности экземпляров."
                )
            serial.ensure_valid()
            if serial.id in by_serial:
                raise InvalidStockExecutionContextError(
                    "Снимок каждого экземпляра передаётся один раз."
                )
            by_serial[serial.id] = serial
        used_items, used_locations, used_lots, used_serials = set(), set(), set(), set()
        for line in lines:
            line.ensure_valid()
            item = by_item.get(line.inventory_item_id)
            if item is None:
                raise InvalidStockExecutionContextError(
                    "Отсутствует снимок товара исполнения."
                )
            line.ensure_compatible(item)
            used_items.add(item.inventory_item_id)
            for dimensions in line.route.dimensions:
                location = by_location.get(dimensions.location_id)
                if location is None:
                    raise InvalidStockExecutionContextError(
                        "Отсутствует снимок фактической локации."
                    )
                used_locations.add(location.id)
                lot = (
                    by_lot.get(dimensions.lot_id)
                    if dimensions.lot_id is not None
                    else None
                )
                serial = (
                    by_serial.get(dimensions.serial_id)
                    if dimensions.serial_id is not None
                    else None
                )
                if dimensions.lot_id is not None:
                    used_lots.add(dimensions.lot_id)
                if dimensions.serial_id is not None:
                    used_serials.add(dimensions.serial_id)
                LocationAvailabilityPolicy.ensure_available(
                    location=location, warehouse=warehouse
                )
                StockDimensionsPolicy.ensure_compatible(
                    dimensions=dimensions,
                    inventory_item=item.stock_snapshot(),
                    location=location,
                    warehouse=warehouse,
                    lot=lot,
                    serial=serial,
                )
                dates = StockTrackingDatesPolicy.resolve(
                    inventory_item=item.tracking_snapshot(),
                    lot_id=dimensions.lot_id,
                    lot=lot,
                    serial=serial,
                )
                StockExpirationPolicy.ensure_operation_allowed(
                    dates=dates,
                    expiration_mode=item.expiration_mode,
                    operation_type=operation_type,
                )

        if (
            used_items != set(by_item)
            or used_locations != set(by_location)
            or used_lots != set(by_lot)
            or used_serials != set(by_serial)
        ):
            raise InvalidStockExecutionContextError(
                "Лишние или отсутствующие снимки контекста исполнения не допускаются."
            )
