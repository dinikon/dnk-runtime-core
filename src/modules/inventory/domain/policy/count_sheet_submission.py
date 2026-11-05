from datetime import datetime

from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.policy.found_count_line import FoundCountLinePolicy
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    CountSheetSourceMismatchError,
    CountSheetTimeError,
    UncountedCountSheetError,
)
from src.modules.inventory.domain.count_sheet.time import normalize_count_sheet_time
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.sheet_source_snapshot import (
    InventoryCountSheetSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.count_sheet_line import CountSheetLinePolicy
from src.modules.inventory.domain.policy.count_sheet_source import (
    CountSheetSourcePolicy,
)
from src.modules.inventory.domain.policy.inventory_count_baseline import (
    InventoryCountBaselinePolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
)
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class CountSheetSubmissionPolicy:
    """Проверяет заполненность, текущие правила товаров и всё основание перед передачей ведомости."""

    @staticmethod
    def ensure_submittable(
        *,
        inventory_count_id: InventoryCountIdVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        baseline_ref: InventoryCountBaselineRefVO,
        lines: tuple[CountLine, ...],
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        submitted_at: datetime,
        warehouse: WarehouseSnapshot | None = None,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> None:
        """Проверяет полный переданный контекст без изменения родителя, запасов, резервов или Ledger."""
        CountSheetSourcePolicy.ensure_sheet_source(
            inventory_count_id=inventory_count_id,
            warehouse_id=warehouse_id,
            owner_id=owner_id,
            baseline_ref=baseline_ref,
            lines=lines,
            inventory_count=inventory_count,
            baseline=baseline,
        )
        submitted = normalize_count_sheet_time(submitted_at)
        if submitted < inventory_count.updated_at:
            raise CountSheetTimeError(
                "Передача не может предшествовать текущему состоянию родителя."
            )
        InventoryCountBaselinePolicy.ensure_unchanged(
            baseline=baseline, locations=locations, positions=positions
        )
        CountSheetSubmissionPolicy.ensure_observations(
            lines=lines,
            warehouse_id=warehouse_id,
            inventory_items=inventory_items,
            locations=locations,
            checked_at=submitted,
            warehouse=warehouse,
            lots=lots,
            serials=serials,
        )

    @staticmethod
    def ensure_observations(
        *,
        lines: tuple[CountLine, ...],
        warehouse_id: WarehouseIdVO,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        checked_at: datetime,
        warehouse: WarehouseSnapshot | None = None,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> None:
        """Переиспользует проверки фактов и найденного контекста для одной ведомости или сводного набора строк."""
        submitted = normalize_count_sheet_time(checked_at)
        if not isinstance(lines, tuple):
            raise InvalidCountLineError(
                "Нужен tuple значений строк для проверки наблюдений."
            )
        for line in lines:
            if not isinstance(line, CountLine):
                raise InvalidCountLineError("Нужны типизированные значения CountLine.")
            line.ensure_valid()
        if not isinstance(warehouse_id, WarehouseIdVO):
            raise CountSheetSourceMismatchError("Нужен ID склада наблюдений.")
        if not isinstance(locations, tuple):
            raise InvalidStockLocationSnapshotError(
                "Нужен tuple текущих адресов наблюдений."
            )
        location_ids = set()
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidStockLocationSnapshotError("Нужны снимки текущих адресов.")
            location.ensure_valid()
            if location.id in location_ids or location.warehouse_id != warehouse_id:
                raise CountSheetSourceMismatchError(
                    "Текущие адреса повторяются или относятся к другому складу."
                )
            location_ids.add(location.id)
        if any(line.dimensions.location_id not in location_ids for line in lines):
            raise CountSheetSourceMismatchError(
                "Для наблюдения отсутствует текущий снимок адреса."
            )
        if not isinstance(inventory_items, tuple):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен tuple текущих учётных снимков товаров."
            )
        items = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemStockSnapshot):
                raise InvalidInventoryItemStockSnapshotError(
                    "Нужны учётные снимки товаров ведомости."
                )
            item.ensure_valid()
            if item.inventory_item_id in items:
                raise CountSheetSourceMismatchError(
                    "Текущий снимок товара повторяется."
                )
            items[item.inventory_item_id] = item
        if set(items) != {line.dimensions.inventory_item_id for line in lines}:
            raise CountSheetSourceMismatchError(
                "Нужны ровно участвующие товары без пропусков или лишних снимков."
            )
        for line in lines:
            if line.counted_qty is None:
                raise UncountedCountSheetError(
                    "Нельзя передать ведомость с непосчитанными строками."
                )
            if line.counted_at > submitted:
                raise CountSheetTimeError(
                    "Передача не может предшествовать фактическому пересчёту."
                )
            CountSheetLinePolicy.ensure_compatible(
                line=line,
                inventory_item=items[line.dimensions.inventory_item_id],
                quantity=line.counted_qty,
            )
        CountSheetSubmissionPolicy._ensure_found_contexts(
            lines=lines,
            warehouse_id=warehouse_id,
            inventory_items=inventory_items,
            locations=locations,
            warehouse=warehouse,
            lots=lots,
            serials=serials,
        )

    @staticmethod
    def _ensure_found_contexts(
        *,
        lines: tuple[CountLine, ...],
        warehouse_id: WarehouseIdVO,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        warehouse: WarehouseSnapshot | None,
        lots: tuple[StockLotSnapshot, ...],
        serials: tuple[StockSerialSnapshot, ...],
    ) -> None:
        """Проверяет ровно необходимые текущие LOT/SERIAL найденных строк после валидации полного набора адресов."""
        found = tuple(line for line in lines if line.origin is CountLineOrigin.FOUND)
        if warehouse is not None or found:
            if not isinstance(warehouse, WarehouseSnapshot):
                raise InvalidWarehouseSnapshotError(
                    "Для FOUND нужен текущий снимок склада."
                )
            warehouse.ensure_valid()
            if warehouse.id != warehouse_id:
                raise CountSheetSourceMismatchError(
                    "Снимок склада относится к другой ведомости."
                )
        if not isinstance(lots, tuple):
            raise InvalidStockLotSnapshotError(
                "Нужен tuple снимков партий найденных строк."
            )
        by_lot = {}
        for lot in lots:
            if (
                not isinstance(lot, StockLotSnapshot)
                or not isinstance(lot.id, StockLotIdVO)
                or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
                or not isinstance(lot.dates, StockDatesVO)
            ):
                raise InvalidStockLotSnapshotError(
                    "Нужен типизированный снимок партии найденного запаса."
                )
            if lot.id in by_lot:
                raise CountSheetSourceMismatchError("Снимок партии повторяется.")
            by_lot[lot.id] = lot
        if not isinstance(serials, tuple):
            raise InvalidStockSerialSnapshotError(
                "Нужен tuple снимков найденных экземпляров."
            )
        by_serial = {}
        for serial in serials:
            if not isinstance(serial, StockSerialSnapshot):
                raise InvalidStockSerialSnapshotError(
                    "Нужен снимок найденного экземпляра."
                )
            serial.ensure_valid()
            if serial.id in by_serial:
                raise CountSheetSourceMismatchError("Снимок экземпляра повторяется.")
            by_serial[serial.id] = serial
        if set(by_lot) != {
            line.dimensions.lot_id
            for line in found
            if line.dimensions.lot_id is not None
        } or set(by_serial) != {
            line.dimensions.serial_id
            for line in found
            if line.dimensions.serial_id is not None
        }:
            raise CountSheetSourceMismatchError(
                "Нужны ровно партии и экземпляры найденных строк без пропусков и лишних снимков."
            )
        by_item = {item.inventory_item_id: item for item in inventory_items}
        by_location = {location.id: location for location in locations}
        for line in found:
            FoundCountLinePolicy.ensure_context(
                line=line,
                warehouse_id=warehouse_id,
                inventory_item=by_item[line.dimensions.inventory_item_id],
                warehouse=warehouse,
                location=by_location[line.dimensions.location_id],
                lot=by_lot.get(line.dimensions.lot_id),
                serial=by_serial.get(line.dimensions.serial_id),
            )
