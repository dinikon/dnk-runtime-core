from datetime import date, datetime
from pydantic import BaseModel
from src.modules.currency.application.exchange_rate.dto.rate_record_dto import (
    RateRecordDTO,
)


class PairResponse(BaseModel):
    """Validated HTTP output for pair response."""

    source: str
    target: str


class RateResponse(BaseModel):
    """Validated HTTP output for rate response."""

    id: str
    pair: PairResponse
    rate: str
    effective_date: date
    provider_code: str
    revision: int
    is_current: bool
    calculated_date: date | None
    created_at: datetime | None
    created_by: str | None

    @classmethod
    def from_dto(cls, r: RateRecordDTO):
        return cls(
            id=str(r.id),
            pair=PairResponse(source=str(r.pair.source), target=str(r.pair.target)),
            rate=format(r.rate, "f"),
            effective_date=r.effective_date,
            provider_code=str(r.provider_code),
            revision=r.revision,
            is_current=r.is_current,
            calculated_date=r.calculated_date,
            created_at=r.created_at,
            created_by=str(r.created_by) if r.created_by else None,
        )


__all__ = ["PairResponse", "RateResponse"]
