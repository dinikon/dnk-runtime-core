from src.modules.currency.application.facade.currency_facade import CurrencyFacade
from src.modules.currency.application.functional_currency.query.get_functional_currency_query import (
    GetFunctionalCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


class GetFunctionalCurrencyUseCase:
    """Public application entrypoint for get functional currency."""

    def __init__(self, facade: CurrencyFacade):
        self.facade = facade

    async def __call__(self, query: GetFunctionalCurrencyQuery) -> CurrencyCodeVO:
        return await self.facade.get_functional_currency(
            tenant_id=query.tenant_id, business_date=query.business_date
        )


__all__ = ["GetFunctionalCurrencyUseCase"]
