from dataclasses import dataclass
from unicodedata import category

from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)


@dataclass(frozen=True, slots=True)
class SupplierSourceNameVO:
    """Отображаемое название источника с сохранением регистра."""

    value: str

    def __post_init__(self) -> None:
        """Требует непустое название без управляющих символов и обрезает пробелы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSupplierSourceValueError(
                "Укажите непустое название источника без управляющих символов."
            )
        object.__setattr__(self, "value", self.value.strip())
