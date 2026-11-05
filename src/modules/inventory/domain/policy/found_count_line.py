from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    CountSheetSourceMismatchError,
    CountSheetLineConflictError,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.stock_dimensions import StockDimensionsPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class FoundCountLinePolicy:
    """Проверяет отсутствие найденных измерений в основании и их текущую складскую идентичность без создания позиции."""

    @staticmethod
    def build_line(
        *,
        identifier: CountLineIdVO,
        dimensions: StockDimensionsVO,
        baseline: InventoryCountBaselineSnapshot,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
        location: StockLocationSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> CountLine:
        """Создаёт локальную FOUND-строку после проверки всего основания и необходимых актуальных снимков."""
        if not isinstance(inventory_item, InventoryItemStockSnapshot):
            raise InvalidInventoryItemStockSnapshotError(
                "Нужен учётный снимок найденного товара."
            )
        inventory_item.ensure_valid()
        line = CountLine.create_found(
            identifier=identifier,
            dimensions=dimensions,
            base_uom=inventory_item.base_uom,
        )
        FoundCountLinePolicy.ensure_sources(lines=(line,), baseline=baseline)
        FoundCountLinePolicy.ensure_context(
            line=line,
            warehouse_id=baseline.warehouse_id,
            inventory_item=inventory_item,
            warehouse=warehouse,
            location=location,
            lot=lot,
            serial=serial,
        )
        return line

    @staticmethod
    def ensure_sources(
        *, lines: tuple[CountLine, ...], baseline: InventoryCountBaselineSnapshot
    ) -> None:
        """Пакетно проверяет владельца, зафиксированные адреса и отсутствие измерений во всём основании, включая нули."""
        if not isinstance(baseline, InventoryCountBaselineSnapshot):
            raise InvalidInventoryCountBaselineError(
                "Нужно полное учётное основание найденных строк."
            )
        baseline.ensure_valid()
        if not isinstance(lines, tuple):
            raise InvalidCountLineError("Нужен tuple найденных строк.")
        known = {position.dimensions for position in baseline.positions}
        locations = {location.id for location in baseline.locations}
        selected, identifiers = set(), set()
        for line in lines:
            if not isinstance(line, CountLine):
                raise InvalidCountLineError("Нужны дочерние найденные строки.")
            line.ensure_valid()
            if line.origin is not CountLineOrigin.FOUND:
                raise InvalidCountLineError("Нужна строка с источником FOUND.")
            if line.id in identifiers or line.dimensions in selected:
                raise CountSheetLineConflictError(
                    "Найденные строки или их измерения повторяются."
                )
            identifiers.add(line.id)
            selected.add(line.dimensions)
            if (
                line.dimensions.owner_id != baseline.owner_id
                or line.dimensions.location_id not in locations
                or line.dimensions in known
            ):
                raise CountSheetSourceMismatchError(
                    "FOUND требует новые измерения выбранного владельца в адресах основания."
                )

    @staticmethod
    def ensure_context(
        *,
        line: CountLine,
        warehouse_id: WarehouseIdVO,
        inventory_item: InventoryItemStockSnapshot,
        warehouse: WarehouseSnapshot,
        location: StockLocationSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> None:
        """Повторно проверяет товар, склад, адрес, партию и экземпляр без фильтра активности или доступности продаж."""
        if not isinstance(line, CountLine):
            raise InvalidCountLineError("Нужна найденная строка.")
        line.ensure_valid()
        if line.origin is not CountLineOrigin.FOUND:
            raise InvalidCountLineError("Контекст найденного запаса требует FOUND.")
        if not isinstance(warehouse_id, WarehouseIdVO):
            raise CountSheetSourceMismatchError("Нужен ID склада ведомости.")
        StockDimensionsPolicy.ensure_compatible(
            dimensions=line.dimensions,
            inventory_item=inventory_item,
            warehouse=warehouse,
            location=location,
            lot=lot,
            serial=serial,
        )
        if warehouse.id != warehouse_id or inventory_item.base_uom != line.base_uom:
            raise CountSheetSourceMismatchError(
                "Склад и базовая единица должны соответствовать найденной строке."
            )
