from datetime import date
from pydantic import BaseModel
from src.modules.currency.application.directory.dto.currency_info_dto import (
    CurrencyInfoDTO,
)


class CurrencyResponse(BaseModel):
    """Validated HTTP output for currency response."""

    code: str
    name: str
    minor_units: int | None
    numeric_code: str | None
    symbol: str | None
    is_active: bool
    valid_from: date | None
    valid_to: date | None

    @classmethod
    def from_dto(cls, info: CurrencyInfoDTO):
        return cls(
            code=str(info.code),
            name=info.name,
            minor_units=info.minor_units,
            numeric_code=info.numeric_code,
            symbol=info.symbol,
            is_active=info.is_active,
            valid_from=info.valid_from,
            valid_to=info.valid_to,
        )


__all__ = ["CurrencyResponse"]
