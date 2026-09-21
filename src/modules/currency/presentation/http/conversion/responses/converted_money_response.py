from datetime import date, datetime
from pydantic import BaseModel
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)


class MoneyResponse(BaseModel):
    """Validated HTTP output for money response."""

    amount: str
    currency: str


class SnapshotResponse(BaseModel):
    """Validated HTTP output for snapshot response."""

    source_currency: str
    target_currency: str
    rate: str
    requested_date: date
    effective_date: date
    converted_at: datetime
    provider_code: str
    derivation: str
    source_rate_ids: list[str]
    bridge_currency: str | None
    policy_version: int
    purpose: str | None
    precision: int | None
    rounding_mode: str | None
    calculation_precision: int | None
    minor_units: int | None


class ConvertedMoneyResponse(BaseModel):
    """Validated HTTP output for converted money response."""

    original: MoneyResponse
    converted: MoneyResponse
    conversion: SnapshotResponse

    @classmethod
    def from_dto(cls, r: ConvertedMoney):
        s = r.conversion
        return cls(
            original=MoneyResponse(
                amount=format(r.original.amount, "f"), currency=str(r.original.currency)
            ),
            converted=MoneyResponse(
                amount=format(r.converted.amount, "f"),
                currency=str(r.converted.currency),
            ),
            conversion=SnapshotResponse(
                source_currency=str(s.source_currency),
                target_currency=str(s.target_currency),
                rate=format(s.rate, "f"),
                requested_date=s.requested_date,
                effective_date=s.effective_date,
                converted_at=s.converted_at,
                provider_code=s.provider_code,
                derivation=s.derivation.value,
                source_rate_ids=[str(i) for i in s.source_rate_ids],
                bridge_currency=str(s.bridge_currency) if s.bridge_currency else None,
                policy_version=s.policy_version,
                purpose=s.purpose,
                precision=s.precision,
                rounding_mode=s.rounding_mode,
                calculation_precision=s.calculation_precision,
                minor_units=s.minor_units,
            ),
        )


__all__ = ["MoneyResponse", "SnapshotResponse", "ConvertedMoneyResponse"]
