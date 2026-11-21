from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.error import InvalidPackagingValueError


@dataclass(frozen=True, slots=True)
class PackagingCodeVO:
    """Непустой пользовательский код типа или варианта упаковки."""

    value: str

    def __post_init__(self) -> None:
        """Убирает внешние пробелы и запрещает управляющие символы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidPackagingValueError("Укажите непустой код упаковки.")
        object.__setattr__(self, "value", self.value.strip())
