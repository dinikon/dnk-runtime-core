from datetime import date, datetime
from pydantic import BaseModel
from src.modules.currency.application.functional_currency.dto.functional_currency_period_dto import (
    FunctionalCurrencyPeriodDTO,
)


class PeriodResponse(BaseModel):
    """Validated HTTP output for period response."""

    id: str
    currency: str
    valid_from: date
    valid_to: date | None
    created_at: datetime
    created_by: str
    reason: str
    activation_emitted_at: datetime | None

    @classmethod
    def from_dto(cls, p: FunctionalCurrencyPeriodDTO):
        return cls(
            id=str(p.id),
            currency=str(p.currency),
            valid_from=p.valid_from,
            valid_to=p.valid_to,
            created_at=p.created_at,
            created_by=str(p.created_by),
            reason=p.reason,
            activation_emitted_at=p.activation_emitted_at,
        )


class FunctionalCurrencyResponse(BaseModel):
    """Validated HTTP output for functional currency response."""

    currency: str


__all__ = ["PeriodResponse", "FunctionalCurrencyResponse"]
