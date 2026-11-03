from dataclasses import dataclass
from datetime import date

from src.modules.inventory.domain.error import InvalidStockDatesError


@dataclass(frozen=True, slots=True)
class StockDatesVO:
    """Необязательные календарные даты партии или экземпляра без оценки просрочки."""

    manufactured_on: date | None = None
    expires_on: date | None = None

    def __post_init__(self) -> None:
        """Принимает только date и не допускает производство позже срока годности."""
        if any(
            value is not None and type(value) is not date
            for value in (self.manufactured_on, self.expires_on)
        ):
            raise InvalidStockDatesError(
                "Даты запасов должны быть date или None, без времени."
            )
        if (
            self.manufactured_on is not None
            and self.expires_on is not None
            and self.manufactured_on > self.expires_on
        ):
            raise InvalidStockDatesError(
                "Дата производства не может быть позже окончания срока годности."
            )
