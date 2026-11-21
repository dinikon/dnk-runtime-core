from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    InvalidCountSheetLineBindingError,
    InvalidCountSheetValueError,
    CountSheetLineConflictError,
    CountSheetSourceMismatchError,
)
from src.modules.inventory.domain.count_sheet.value_object.line_binding import (
    CountSheetLineBindingVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.policy.found_count_line import FoundCountLinePolicy
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InvalidInventoryCountSheetSourceError,
    InventoryCountStatusError,
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
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class CountSheetSourcePolicy:
    """Согласует запущенную инвентаризацию, её основание и выбранные строки без владения чужими корнями."""

    @staticmethod
    def ensure_parent(
        *,
        inventory_count_id: InventoryCountIdVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        baseline_ref: InventoryCountBaselineRefVO,
        inventory_count: InventoryCountSheetSourceSnapshot,
    ) -> None:
        """Проверяет текущего исполняемого родителя для отзыва без требования актуальности физического основания."""
        if not isinstance(inventory_count, InventoryCountSheetSourceSnapshot):
            raise InvalidInventoryCountSheetSourceError(
                "Нужен текущий снимок родителя ведомости."
            )
        inventory_count.ensure_valid()
        if inventory_count.status is not InventoryCountStatus.IN_PROGRESS:
            raise InventoryCountStatusError(
                "Изменение ведомости требует IN_PROGRESS родителя."
            )
        if (
            not isinstance(inventory_count_id, InventoryCountIdVO)
            or not isinstance(warehouse_id, WarehouseIdVO)
            or not isinstance(owner_id, StockOwnerIdVO)
            or not isinstance(baseline_ref, InventoryCountBaselineRefVO)
        ):
            raise InvalidCountSheetValueError(
                "Нужны типизированные сохранённые ссылки ведомости."
            )
        baseline_ref.ensure_valid()
        if (
            inventory_count.id != inventory_count_id
            or inventory_count.warehouse_id != warehouse_id
            or inventory_count.owner_id != owner_id
            or inventory_count.baseline != baseline_ref
        ):
            raise CountSheetSourceMismatchError(
                "Снимок родителя не соответствует ведомости."
            )

    @staticmethod
    def ensure_compatible(
        *,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
    ) -> None:
        """Требует IN_PROGRESS и то же основание, сохраняя различие текущей и исторической версий родителя."""
        if not isinstance(inventory_count, InventoryCountSheetSourceSnapshot):
            raise InvalidInventoryCountSheetSourceError(
                "Нужен снимок текущей инвентаризации для ведомости."
            )
        inventory_count.ensure_valid()
        if inventory_count.status is not InventoryCountStatus.IN_PROGRESS:
            raise InventoryCountStatusError(
                "Ведомость требует запущенную инвентаризацию."
            )
        if not isinstance(baseline, InventoryCountBaselineSnapshot):
            raise InvalidInventoryCountBaselineError(
                "Нужно учётное основание ведомости."
            )
        baseline.ensure_valid()
        reference = inventory_count.baseline
        if (
            reference is None
            or reference.id != baseline.id
            or reference.snapshot_at != baseline.snapshot_at
            or inventory_count.id != baseline.inventory_count_id
            or inventory_count.warehouse_id != baseline.warehouse_id
            or inventory_count.owner_id != baseline.owner_id
            or inventory_count.scope != baseline.scope
            or inventory_count.version <= baseline.inventory_count_version
        ):
            raise CountSheetSourceMismatchError(
                "Основание не соответствует запущенной инвентаризации."
            )

    @staticmethod
    def build_lines(
        *,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        bindings: tuple[CountSheetLineBindingVO, ...],
    ) -> tuple[CountLine, ...]:
        """Строит непустой фиксированный состав только из выбранных существующих позиций основания."""
        CountSheetSourcePolicy.ensure_compatible(
            inventory_count=inventory_count, baseline=baseline
        )
        if not isinstance(bindings, tuple) or not bindings:
            raise InvalidCountSheetLineBindingError(
                "Нужен непустой tuple назначений строк позициям основания."
            )
        positions = {row.id: row for row in baseline.positions}
        line_ids, position_ids, lines = set(), set(), []
        for binding in bindings:
            if not isinstance(binding, CountSheetLineBindingVO):
                raise InvalidCountSheetLineBindingError(
                    "Нужно назначение CountSheetLineBindingVO."
                )
            binding.ensure_valid()
            if binding.line_id in line_ids or binding.position_id in position_ids:
                raise CountSheetLineConflictError(
                    "ID строк и позиции ведомости не должны повторяться."
                )
            line_ids.add(binding.line_id)
            position_ids.add(binding.position_id)
            position = positions.get(binding.position_id)
            if position is None:
                raise CountSheetSourceMismatchError(
                    "Выбранная позиция отсутствует в учётном основании."
                )
            lines.append(
                CountLine.create(identifier=binding.line_id, position=position)
            )
        return tuple(sorted(lines, key=lambda line: line.id.uuid.int))

    @staticmethod
    def ensure_sheet_source(
        *,
        inventory_count_id: InventoryCountIdVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        baseline_ref: InventoryCountBaselineRefVO,
        lines: tuple[CountLine, ...],
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
    ) -> None:
        """Повторно проверяет сохранённые ссылки ведомости и все исходные поля строк относительно полного основания."""
        CountSheetSourcePolicy.ensure_compatible(
            inventory_count=inventory_count, baseline=baseline
        )
        if (
            not isinstance(inventory_count_id, InventoryCountIdVO)
            or not isinstance(warehouse_id, WarehouseIdVO)
            or not isinstance(owner_id, StockOwnerIdVO)
            or not isinstance(baseline_ref, InventoryCountBaselineRefVO)
            or not isinstance(lines, tuple)
            or not lines
        ):
            raise InvalidCountSheetValueError(
                "Нужен полный типизированный состав ссылок и строк ведомости."
            )
        baseline_ref.ensure_valid()
        if (
            inventory_count_id != inventory_count.id
            or warehouse_id != inventory_count.warehouse_id
            or owner_id != inventory_count.owner_id
            or baseline_ref != inventory_count.baseline
        ):
            raise CountSheetSourceMismatchError(
                "Ведомость относится к другой инвентаризации или основанию."
            )
        positions = {row.id: row for row in baseline.positions}
        ids, selected, dimensions, found = set(), set(), set(), []
        for line in lines:
            if not isinstance(line, CountLine):
                raise InvalidCountLineError("Нужны дочерние строки ведомости.")
            line.ensure_valid()
            if (
                line.id in ids
                or (line.position_id is not None and line.position_id in selected)
                or line.dimensions in dimensions
            ):
                raise CountSheetLineConflictError(
                    "Строки, позиции и измерения ведомости должны быть уникальны."
                )
            ids.add(line.id)
            if line.position_id is not None:
                selected.add(line.position_id)
            dimensions.add(line.dimensions)
            if line.origin is CountLineOrigin.FOUND:
                found.append(line)
            elif positions.get(line.position_id) != line.baseline_position_snapshot():
                raise CountSheetSourceMismatchError(
                    "Учётные поля строки не соответствуют позиции основания."
                )
        if found:
            FoundCountLinePolicy.ensure_sources(lines=tuple(found), baseline=baseline)
