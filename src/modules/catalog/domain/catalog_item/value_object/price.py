from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class PriceSpecificationVO:
    """Цена и скидка в одной валюте с полуоткрытым UTC-интервалом."""

    regular_price: Decimal
    currency: str
    sale_price: Decimal | None = None
    date_on_sale_from: datetime | None = None
    date_on_sale_to: datetime | None = None

    def __post_init__(self) -> None:
        """Проверяет точные суммы, валюту и согласованность периода скидки."""
        prices = (
            (self.regular_price,)
            if self.sale_price is None
            else (self.regular_price, self.sale_price)
        )
        if any(
            not isinstance(v, Decimal)
            or not v.is_finite()
            or v < 0
            or v.as_tuple().exponent < -6
            for v in prices
        ):
            raise InvalidCatalogValueError(
                "Цена должна быть конечным неотрицательным Decimal с точностью до 6 знаков."
            )
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise InvalidCatalogValueError("Нужен ISO-код валюты.")
        if self.sale_price is not None and self.sale_price > self.regular_price:
            raise InvalidCatalogValueError("Цена скидки превышает обычную цену.")
        bounds = (self.date_on_sale_from, self.date_on_sale_to)
        if any(
            v is not None and (v.tzinfo is None or v.utcoffset() is None)
            for v in bounds
        ):
            raise InvalidCatalogValueError("Дата скидки требует timezone.")
        if self.sale_price is None and any(v is not None for v in bounds):
            raise InvalidCatalogValueError("Период требует цену скидки.")
        if all(v is not None for v in bounds) and bounds[0] > bounds[1]:
            raise InvalidCatalogValueError("Начало скидки позже окончания.")

    def at(self, as_of: datetime) -> Decimal:
        """Вычисляет текущую цену по времени, переданному вызывающей стороной."""
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise InvalidCatalogValueError("Время расчёта требует timezone.")
        active = (
            self.date_on_sale_from is None or as_of >= self.date_on_sale_from
        ) and (self.date_on_sale_to is None or as_of < self.date_on_sale_to)
        return (
            self.sale_price
            if self.sale_price is not None and active
            else self.regular_price
        )
