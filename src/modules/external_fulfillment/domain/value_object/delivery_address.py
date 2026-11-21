from dataclasses import dataclass
from unicodedata import category

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)


@dataclass(frozen=True, slots=True)
class SupplierDeliveryAddressVO:
    """Фиксирует адрес доставки покупателю на момент создания заявки."""

    country_code: str
    city: str
    address_line: str
    postal_code: str | None = None

    def __post_init__(self) -> None:
        """Проверяет двухбуквенный код страны и нормализует заполненные части адреса."""
        country = self._clean(self.country_code)
        if len(country) != 2 or not country.isascii() or not country.isalpha():
            raise InvalidSupplierFulfillmentValueError(
                "Адрес требует двухбуквенный код страны."
            )
        object.__setattr__(self, "country_code", country.upper())
        object.__setattr__(self, "city", self._clean(self.city))
        object.__setattr__(self, "address_line", self._clean(self.address_line))
        if self.postal_code is not None:
            object.__setattr__(self, "postal_code", self._clean(self.postal_code))

    @staticmethod
    def _clean(value: str) -> str:
        """Обрезает пробелы и запрещает пустые части адреса и управляющие символы."""
        if (
            not isinstance(value, str)
            or not value.strip()
            or any(category(char) in ("Cc", "Cf") for char in value)
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Заполненные части адреса должны быть непустыми строками."
            )
        return value.strip()
