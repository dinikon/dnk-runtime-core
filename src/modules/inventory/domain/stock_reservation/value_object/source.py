from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_reservation.error import (
    InvalidReservationSourceError,
)


@dataclass(frozen=True, slots=True)
class ReservationSourceVO:
    """Сохраняет систему и ссылку на конкретную строку обязательства без чужого агрегата."""

    system: str
    reference: str

    def __post_init__(self) -> None:
        """Нормализует края непустых строк, сохраняя регистр и запрещая управляющие символы."""
        for name in ("system", "reference"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or any(category(char) in ("Cc", "Cf") for char in value)
            ):
                raise InvalidReservationSourceError(
                    "Укажите систему и ссылку строки обязательства без управляющих символов."
                )
            object.__setattr__(self, name, value.strip())
