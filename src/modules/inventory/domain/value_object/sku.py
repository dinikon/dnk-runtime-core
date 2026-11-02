from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.error import InvalidSkuError


@dataclass(frozen=True, slots=True)
class SkuVO:
    """Ручной SKU до 25 символов с каноническим регистронезависимым значением."""

    value: str

    def __post_init__(self) -> None:
        """Применяет trim и casefold, проверяет длину и управляющие символы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSkuError("Укажите непустой SKU без управляющих символов.")
        value = self.value.strip().casefold()
        if len(value) > 25:
            raise InvalidSkuError(
                "SKU после нормализации должен содержать до 25 символов."
            )
        object.__setattr__(self, "value", value)
