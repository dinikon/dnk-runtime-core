"""Снимки справочников для изолированных тестов физического и стоимостного журналов."""

from typing import TypedDict

from src.modules.inventory.domain.inventory_item.snapshot import (
    InventoryItemTrackingSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class PostingTrackingContext(TypedDict):
    """Передаёт конкретные коллекции справочных снимков тестового проведения."""

    inventory_items: tuple[InventoryItemTrackingSnapshot, ...]
    lots: tuple[StockLotSnapshot, ...]
    serials: tuple[StockSerialSnapshot, ...]


def posting_tracking_context(
    positions: tuple[StockPositionSnapshot, ...],
) -> PostingTrackingContext:
    """Готовит справочники без контроля срока для исторических позиций стоимостных фикстур."""
    items = {}
    lots = {}
    serials = {}
    for position in positions:
        if not isinstance(position, StockPositionSnapshot):
            continue
        dims = position.dimensions
        mode = (
            (
                TrackingMode.LOT_AND_SERIAL
                if dims.lot_id is not None
                else TrackingMode.SERIAL
            )
            if dims.serial_id is not None
            else (TrackingMode.LOT if dims.lot_id is not None else TrackingMode.NONE)
        )
        items[dims.inventory_item_id] = InventoryItemTrackingSnapshot(
            dims.inventory_item_id, mode, ExpirationMode.NONE
        )
        if dims.lot_id is not None:
            lots[dims.lot_id] = StockLotSnapshot(
                dims.lot_id, dims.inventory_item_id, StockDatesVO()
            )
        if dims.serial_id is not None:
            serials[dims.serial_id] = StockSerialSnapshot(
                dims.serial_id, dims.inventory_item_id, dims.lot_id
            )
    return dict(
        inventory_items=tuple(items.values()),
        lots=tuple(lots.values()),
        serials=tuple(serials.values()),
    )
