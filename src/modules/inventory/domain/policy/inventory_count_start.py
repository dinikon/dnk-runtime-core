from datetime import datetime

from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InvalidInventoryCountStartPlanError,
    InventoryCountContextMismatchError,
    InventoryCountStatusError,
    InventoryCountTimeError,
    InventoryCountVersionConflictError,
)
from src.modules.inventory.domain.inventory_count.start_plan_snapshot import (
    InventoryCountStartPlanSnapshot,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_id import (
    InventoryCountBaselineIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.policy.inventory_count_confirmation import (
    InventoryCountConfirmationPolicy,
)
from src.modules.inventory.domain.stock_location.error import StockLocationInactiveError
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class InventoryCountStartPolicy:
    """Строит учётное основание и согласует его с текущим подтверждённым планом без изменения запасов."""

    @staticmethod
    def build_baseline(
        *,
        plan: InventoryCountStartPlanSnapshot,
        identifier: InventoryCountBaselineIdVO,
        snapshot_at: datetime,
        warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
    ) -> InventoryCountBaselineSnapshot:
        """Фиксирует переданный согласованный набор позиций; полнота чтения остаётся внешнему сценарию."""
        InventoryCountStartPolicy._ensure_plan(plan)
        baseline = InventoryCountBaselineSnapshot(
            identifier,
            plan.id,
            plan.version,
            plan.warehouse_id,
            plan.owner_id,
            plan.scope,
            normalize_inventory_count_time(snapshot_at),
            locations,
            positions,
        )
        InventoryCountStartPolicy.ensure_compatible(
            plan=plan,
            baseline=baseline,
            warehouse=warehouse,
            locations=locations,
        )
        return baseline

    @staticmethod
    def ensure_compatible(
        *,
        plan: InventoryCountStartPlanSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        warehouse: WarehouseSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
    ) -> None:
        """Повторно проверяет основание, точную версию плана, склад и текущие адреса перед запуском."""
        InventoryCountStartPolicy._ensure_plan(plan)
        if not isinstance(baseline, InventoryCountBaselineSnapshot):
            raise InvalidInventoryCountBaselineError(
                "Нужно учётное основание инвентаризации."
            )
        baseline.ensure_valid()
        if baseline.inventory_count_version != plan.version:
            raise InventoryCountVersionConflictError(
                "Основание построено для другой версии плана."
            )
        if (
            baseline.inventory_count_id != plan.id
            or baseline.warehouse_id != plan.warehouse_id
            or baseline.owner_id != plan.owner_id
            or baseline.scope != plan.scope
        ):
            raise InventoryCountContextMismatchError(
                "Основание не соответствует текущему плану инвентаризации."
            )
        if baseline.snapshot_at < plan.updated_at:
            raise InventoryCountTimeError(
                "Момент снимка не может предшествовать подтверждённому плану."
            )
        InventoryCountConfirmationPolicy.ensure_warehouse(
            warehouse_id=plan.warehouse_id, warehouse=warehouse
        )
        current = InventoryCountBaselineSnapshot(
            baseline.id,
            plan.id,
            plan.version,
            plan.warehouse_id,
            plan.owner_id,
            plan.scope,
            baseline.snapshot_at,
            locations,
            (),
        )
        current.ensure_valid()
        if {row.id for row in locations} != {row.id for row in baseline.locations}:
            raise InventoryCountContextMismatchError(
                "Текущие адреса не соответствуют адресам основания."
            )
        if plan.scope.count_type is CountType.PARTIAL and any(
            not row.is_active for row in locations
        ):
            raise StockLocationInactiveError(
                "Выбранные адреса частичной проверки должны быть активны."
            )

    @staticmethod
    def _ensure_plan(plan: InventoryCountStartPlanSnapshot) -> None:
        """Требует типизированный снимок подтверждённого плана без передачи самого агрегата."""
        if not isinstance(plan, InventoryCountStartPlanSnapshot):
            raise InvalidInventoryCountStartPlanError(
                "Нужен снимок текущего плана запуска."
            )
        plan.ensure_valid()
        if plan.status is not InventoryCountStatus.CONFIRMED:
            raise InventoryCountStatusError(
                "Запустить можно только подтверждённую инвентаризацию."
            )
