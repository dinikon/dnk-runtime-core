from dataclasses import replace

from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InventoryCountBaselineChangedError,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)


class InventoryCountBaselinePolicy:
    """Запрещает использовать старое основание после изменения области или физических позиций."""

    @staticmethod
    def ensure_unchanged(
        *,
        baseline: InventoryCountBaselineSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
    ) -> None:
        """Проверяет весь текущий состав и версии, включая новые позиции; не блокирует дальнейшие движения."""
        if not isinstance(baseline, InventoryCountBaselineSnapshot):
            raise InvalidInventoryCountBaselineError(
                "Нужно учётное основание инвентаризации."
            )
        baseline.ensure_valid()
        current = replace(baseline, locations=locations, positions=positions)
        current.ensure_valid()
        if {row.id for row in locations} != {row.id for row in baseline.locations} or {
            row.id: row for row in positions
        } != {row.id: row for row in baseline.positions}:
            raise InventoryCountBaselineChangedError(
                "Основание изменилось: нужен повторный пересчёт по новому основанию."
            )
