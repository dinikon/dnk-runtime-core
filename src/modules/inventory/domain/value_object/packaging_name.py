from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.error import InvalidPackagingValueError


@dataclass(frozen=True, slots=True)
class PackagingNameVO:
    """Пользовательское название типа тары или варианта упаковки товара."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет непустое название и сохраняет его после trim."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidPackagingValueError("Укажите непустое название упаковки.")
        object.__setattr__(self, "value", self.value.strip())
