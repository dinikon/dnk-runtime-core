from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_location.error import InvalidLocationNameError


@dataclass(frozen=True, slots=True)
class LocationNameVO:
    """Обязательное пользовательское название адреса с сохранением регистра."""

    value: str

    def __post_init__(self) -> None:
        """Убирает внешние пробелы и запрещает пустые и управляющие значения."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidLocationNameError(
                "Укажите непустое строковое название локации."
            )
        object.__setattr__(self, "value", self.value.strip())
