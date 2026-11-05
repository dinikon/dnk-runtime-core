from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_id import (
    InventoryCountBaselineIdVO,
)


@dataclass(frozen=True, slots=True)
class InventoryCountBaselineRefVO:
    """Компактная ссылка на основание с моментом снимка без коллекции складских позиций."""

    id: InventoryCountBaselineIdVO
    snapshot_at: datetime

    def __post_init__(self) -> None:
        """Нормализует время собственного значения и проверяет типизированную ссылку."""
        object.__setattr__(
            self, "snapshot_at", normalize_inventory_count_time(self.snapshot_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Проверяет ID основания и UTC-время при передаче или восстановлении ссылки."""
        if not isinstance(self.id, InventoryCountBaselineIdVO):
            raise InvalidInventoryCountBaselineError("Нужен ID учётного основания.")
        normalize_inventory_count_time(self.snapshot_at)
        if self.snapshot_at.utcoffset() != timedelta(0):
            raise InvalidInventoryCountBaselineError(
                "Ссылка должна хранить время в UTC."
            )
