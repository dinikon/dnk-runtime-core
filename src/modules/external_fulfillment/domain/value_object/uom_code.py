from dataclasses import dataclass
from unicodedata import category

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentUomCodeVO:
    """Хранит согласованный код базовой единицы внешней строки."""

    value: str

    def __post_init__(self) -> None:
        """Обрезает пробелы и проверяет непустой код с сохранением регистра."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужен непустой код базовой единицы."
            )
        object.__setattr__(self, "value", self.value.strip())
