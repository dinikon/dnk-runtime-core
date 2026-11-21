from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.warehouse.error import InvalidWarehouseCodeError


@dataclass(frozen=True, slots=True)
class WarehouseCodeVO:
    """Канонический регистронезависимый пользовательский код склада."""

    value: str

    def __post_init__(self) -> None:
        """Применяет trim и casefold, запрещая пустоту и управляющие символы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidWarehouseCodeError(
                "Укажите непустой строковый код склада без управляющих символов."
            )
        object.__setattr__(self, "value", self.value.strip().casefold())
