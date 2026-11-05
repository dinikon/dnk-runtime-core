from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountResultError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)


@dataclass(frozen=True, slots=True)
class CountSheetRevisionVO:
    """Фиксирует ID, версию, состояние и время одной учтённой либо исключённой ведомости."""

    id: CountSheetIdVO
    version: int
    status: CountSheetStatus
    updated_at: datetime

    def __post_init__(self) -> None:
        """Нормализует собственное время и проверяет номинальные значения ревизии."""
        object.__setattr__(
            self, "updated_at", normalize_inventory_count_time(self.updated_at)
        )
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Проверяет строгую версию без bool, статус ведомости и UTC-время ревизии."""
        if (
            not isinstance(self.id, CountSheetIdVO)
            or type(self.version) is not int
            or self.version < 0
            or not isinstance(self.status, CountSheetStatus)
        ):
            raise InvalidInventoryCountResultError(
                "Нужна типизированная ревизия ведомости."
            )
        normalize_inventory_count_time(self.updated_at)
        if self.updated_at.utcoffset() != timedelta(0):
            raise InvalidInventoryCountResultError(
                "Время ревизии должно храниться в UTC."
            )
