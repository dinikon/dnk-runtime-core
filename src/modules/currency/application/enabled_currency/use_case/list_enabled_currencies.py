from src.modules.currency.application.enabled_currency.query.list_enabled_currencies_query import (
    ListEnabledCurrenciesQuery,
)
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


class ListEnabledCurrenciesUseCase:
    """Execute the list enabled currencies read scenario."""

    def __init__(self, repository: EnabledCurrencyRepository):
        self.repository = repository

    async def __call__(
        self, query: ListEnabledCurrenciesQuery
    ) -> tuple[CurrencyCodeVO, ...]:
        return tuple(
            sorted(await self.repository.enabled(tenant_id=query.tenant_id), key=str)
        )


__all__ = ["ListEnabledCurrenciesUseCase"]
