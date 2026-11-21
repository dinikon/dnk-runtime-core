from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.stock_serial.error import InvalidSerialNumberError


@dataclass(frozen=True, slots=True)
class SerialNumberVO:
    """Обязательный серийный номер с сохранением регистра и ведущих нулей."""

    value: str

    def __post_init__(self) -> None:
        """Убирает внешние пробелы и запрещает пустые и управляющие значения."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSerialNumberError("Укажите непустой строковый серийный номер.")
        object.__setattr__(self, "value", self.value.strip())
