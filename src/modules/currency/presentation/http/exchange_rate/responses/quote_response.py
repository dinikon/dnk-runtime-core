from datetime import date
from pydantic import BaseModel
from src.modules.currency.application.conversion.dto.rate_quote_dto import RateQuoteDTO
from src.modules.currency.presentation.http.exchange_rate.responses.rate_response import (
    PairResponse,
)


class QuoteResponse(BaseModel):
    """Validated HTTP output for quote response."""

    pair: PairResponse
    rate: str
    requested_date: date
    effective_date: date
    provider_code: str
    derivation: str
    source_rate_ids: list[str]
    bridge_currency: str | None

    @classmethod
    def from_dto(cls, q: RateQuoteDTO):
        return cls(
            pair=PairResponse(source=str(q.pair.source), target=str(q.pair.target)),
            rate=format(q.rate, "f"),
            requested_date=q.requested_date,
            effective_date=q.effective_date,
            provider_code=str(q.provider_code),
            derivation=q.derivation.value,
            source_rate_ids=[str(i) for i in q.source_rate_ids],
            bridge_currency=str(q.bridge_currency) if q.bridge_currency else None,
        )


__all__ = ["QuoteResponse"]
