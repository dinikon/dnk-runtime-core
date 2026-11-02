from dataclasses import dataclass
from datetime import date

from src.modules.inventory.domain.stock_lot.error import InvalidLotDatesError


@dataclass(frozen=True, slots=True)
class LotDatesVO:
    """Необязательные календарные даты партии без правил срока на дату операции."""

    manufactured_on: date | None = None
    expires_on: date | None = None

    def __post_init__(self) -> None:
        """Принимает только date и не допускает производство позже срока годности."""
        if any(
            value is not None and type(value) is not date
            for value in (self.manufactured_on, self.expires_on)
        ):
            raise InvalidLotDatesError(
                "Даты партии должны быть date или None, без времени."
            )
        if (
            self.manufactured_on is not None
            and self.expires_on is not None
            and self.manufactured_on > self.expires_on
        ):
            raise InvalidLotDatesError(
                "Дата производства не может быть позже окончания срока годности."
            )
