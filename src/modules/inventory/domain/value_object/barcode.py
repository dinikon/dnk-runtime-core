from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.error import InvalidBarcodeError


@dataclass(frozen=True, slots=True)
class BarcodeVO:
    """Строковый штрихкод, сохраняющий ведущие нули и регистр."""

    value: str

    def __post_init__(self) -> None:
        """Убирает внешние пробелы и отклоняет пустой или управляющий ввод."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidBarcodeError("Укажите непустой строковый штрихкод.")
        object.__setattr__(self, "value", self.value.strip())
