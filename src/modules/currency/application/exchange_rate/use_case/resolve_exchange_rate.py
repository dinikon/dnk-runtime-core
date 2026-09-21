from src.modules.currency.application.conversion.dto.rate_quote_dto import RateQuoteDTO
from src.modules.currency.application.exchange_rate.query.resolve_exchange_rate_query import (
    ResolveExchangeRateQuery,
)
from src.modules.currency.application.facade.currency_facade import CurrencyFacade


class ResolveExchangeRateUseCase:
    """Public application entrypoint for resolve exchange rate."""

    def __init__(self, facade: CurrencyFacade):
        self.facade = facade

    async def __call__(self, query: ResolveExchangeRateQuery) -> RateQuoteDTO:
        return await self.facade.resolve_rate(
            tenant_id=query.tenant_id,
            source=query.source,
            target=query.target,
            date=query.business_date,
        )


__all__ = ["ResolveExchangeRateUseCase"]
