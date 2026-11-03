from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.warehouse.error import InvalidWarehouseNameError


@dataclass(frozen=True, slots=True)
class WarehouseNameVO:
    """Обязательное пользовательское название склада с сохранением регистра."""

    value: str

    def __post_init__(self) -> None:
        """Убирает внешние пробелы и запрещает пустые и управляющие значения."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidWarehouseNameError(
                "Укажите непустое строковое название склада."
            )
        object.__setattr__(self, "value", self.value.strip())
