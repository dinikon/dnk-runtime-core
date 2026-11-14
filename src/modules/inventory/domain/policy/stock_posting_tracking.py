from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_expiration import StockExpirationPolicy
from src.modules.inventory.domain.policy.stock_tracking_dates import (
    StockTrackingDatesPolicy,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.error import InvalidPostingContextError
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class StockPostingTrackingPolicy:
    """Повторно проверяет текущую прослеживаемость и срок партий при новом проведении."""

    @staticmethod
    def ensure_compatible(
        *,
        operation_type: StockOperationType,
        positions: tuple[StockPositionSnapshot, ...],
        inventory_items: tuple[InventoryItemTrackingSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...],
        serials: tuple[StockSerialSnapshot, ...],
    ) -> None:
        """Требует ровно участвующие снимки и заполненный срок партии перед поступлением REQUIRED."""
        if not all(
            isinstance(values, tuple)
            for values in (positions, inventory_items, lots, serials)
        ):
            raise InvalidPostingContextError(
                "Контекст проведения передаётся в tuple снимков."
            )
        by_item: dict[InventoryItemIdVO, InventoryItemTrackingSnapshot] = {}
        by_lot: dict[StockLotIdVO, StockLotSnapshot] = {}
        by_serial: dict[StockSerialIdVO, StockSerialSnapshot] = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemTrackingSnapshot):
                raise InvalidPostingContextError(
                    "Нужны снимки настроек товара проведения."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InvalidPostingContextError("Повтор снимка товара проведения.")
            by_item[item.inventory_item_id] = item
        for lot in lots:
            if (
                not isinstance(lot, StockLotSnapshot)
                or not isinstance(lot.id, StockLotIdVO)
                or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
                or not isinstance(lot.dates, StockDatesVO)
            ):
                raise InvalidPostingContextError(
                    "Нужны типизированные снимки партий проведения."
                )
            if lot.id in by_lot:
                raise InvalidPostingContextError("Повтор снимка партии проведения.")
            by_lot[lot.id] = lot
        for serial in serials:
            if not isinstance(serial, StockSerialSnapshot):
                raise InvalidPostingContextError(
                    "Нужны снимки идентичности экземпляров."
                )
            serial.ensure_valid()
            if serial.id in by_serial:
                raise InvalidPostingContextError("Повтор снимка экземпляра проведения.")
            by_serial[serial.id] = serial
        used_items: set[InventoryItemIdVO] = set()
        used_lots: set[StockLotIdVO] = set()
        used_serials: set[StockSerialIdVO] = set()
        for position in positions:
            position.ensure_valid()
            dimensions = position.dimensions
            item = by_item.get(dimensions.inventory_item_id)
            if item is None:
                raise InvalidPostingContextError(
                    "Отсутствует снимок товара проведения."
                )
            used_items.add(item.inventory_item_id)
            if dimensions.lot_id is not None:
                used_lots.add(dimensions.lot_id)
            if dimensions.serial_id is not None:
                used_serials.add(dimensions.serial_id)
            serial = (
                by_serial.get(dimensions.serial_id)
                if dimensions.serial_id is not None
                else None
            )
            if dimensions.serial_id is not None and (
                serial is None or serial.id != dimensions.serial_id
            ):
                raise InvalidPostingContextError(
                    "Отсутствует снимок экземпляра проведения."
                )
            dates = StockTrackingDatesPolicy.resolve(
                inventory_item=item,
                lot_id=dimensions.lot_id,
                lot=(
                    by_lot.get(dimensions.lot_id)
                    if dimensions.lot_id is not None
                    else None
                ),
                serial=serial,
            )
            StockExpirationPolicy.ensure_operation_allowed(
                dates=dates,
                expiration_mode=item.expiration_mode,
                operation_type=operation_type,
            )
        if (
            used_items != set(by_item)
            or used_lots != set(by_lot)
            or used_serials != set(by_serial)
        ):
            raise InvalidPostingContextError(
                "Нужны ровно участвующие снимки товаров, партий и экземпляров."
            )
