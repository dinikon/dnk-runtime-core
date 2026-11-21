from dataclasses import dataclass
from unicodedata import category

from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    InvalidSupplierOfferValueError,
)


@dataclass(frozen=True, slots=True)
class SupplierSkuVO:
    """Хранит SKU из системы поставщика с его регистром и ведущими нулями."""

    value: str

    def __post_init__(self) -> None:
        """Обрезает пробелы по краям и требует непустой код без управляющих символов."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSupplierOfferValueError(
                "Укажите непустой SKU поставщика без управляющих символов."
            )
        object.__setattr__(self, "value", self.value.strip())
