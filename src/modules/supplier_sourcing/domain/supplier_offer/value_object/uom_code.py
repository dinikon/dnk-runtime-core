from dataclasses import dataclass
from unicodedata import category

from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    InvalidSupplierOfferValueError,
)


@dataclass(frozen=True, slots=True)
class SupplierOfferUomCodeVO:
    """Фиксирует код базовой единицы товара для цены и количеств предложения."""

    value: str

    def __post_init__(self) -> None:
        """Принимает непустой код единицы с сохранением регистра."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSupplierOfferValueError(
                "Укажите непустой код единицы предложения без управляющих символов."
            )
        object.__setattr__(self, "value", self.value.strip())
