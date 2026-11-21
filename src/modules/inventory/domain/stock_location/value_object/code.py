from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_location.error import InvalidLocationCodeError


@dataclass(frozen=True, slots=True)
class LocationCodeVO:
    """Канонический регистронезависимый код адреса внутри склада."""

    value: str

    def __post_init__(self) -> None:
        """Применяет trim и casefold, запрещая пустоту и управляющие символы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidLocationCodeError("Укажите непустой строковый код локации.")
        object.__setattr__(self, "value", self.value.strip().casefold())
