from datetime import datetime

from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
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
        InventoryCountBaselinePolicy.ensure_unchanged(
            baseline=baseline, locations=locations, positions=positions
        )
