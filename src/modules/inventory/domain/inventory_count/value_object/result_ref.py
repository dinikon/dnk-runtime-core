from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountResultError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.result_id import (
    InventoryCountResultIdVO,
)


@dataclass(frozen=True, slots=True)
class InventoryCountResultRefVO:
    """Компактная ссылка на сводный результат и его момент подготовки без коллекции наблюдений."""

    id: InventoryCountResultIdVO
    prepared_at: datetime

    def __post_init__(self) -> None:
        """Нормализует собственный момент в UTC и проверяет типизированный ID результата."""
        object.__setattr__(
            self, "prepared_at", normalize_inventory_count_time(self.prepared_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Проверяет собственные типы ссылки и UTC-хранение момента подготовки."""
        if not isinstance(self.id, InventoryCountResultIdVO):
            raise InvalidInventoryCountResultError("Нужен ID сводного результата.")
        normalize_inventory_count_time(self.prepared_at)
        if self.prepared_at.utcoffset() != timedelta(0):
            raise InvalidInventoryCountResultError(
                "Момент результата должен храниться в UTC."
            )
