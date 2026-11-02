from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.error import InvalidSkuError


@dataclass(frozen=True, slots=True)
class SkuVO:
    """Ручной SKU с точным регистрозависимым сравнением после trim."""

    value: str

    def __post_init__(self) -> None:
        """Отклоняет пустое значение и управляющие символы, сохраняет регистр."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSkuError("Укажите непустой SKU без управляющих символов.")
        object.__setattr__(self, "value", self.value.strip())
