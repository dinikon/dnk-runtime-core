from dataclasses import dataclass

from src.modules.inventory.domain.availability_pool.error import (
    InvalidAvailabilityPoolReservationSnapshotError,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class AvailabilityPoolReservationSnapshot:
    """Передаёт идентичность, область и единицу пула без подтверждения свободного количества."""

    id: AvailabilityPoolIdVO
    key: AvailabilityPoolKeyVO
    base_uom: UomCodeVO

    def ensure_valid(self) -> None:
        """Проверяет типы и известную единицу привязки без счётчиков и версии пула."""
        if (
            not isinstance(self.id, AvailabilityPoolIdVO)
            or not isinstance(self.key, AvailabilityPoolKeyVO)
            or not isinstance(self.base_uom, UomCodeVO)
        ):
            raise InvalidAvailabilityPoolReservationSnapshotError(
                "Нужен типизированный снимок идентичности, ключа и единицы пула."
            )
        get_uom(self.base_uom)
