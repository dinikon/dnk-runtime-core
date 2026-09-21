from src.modules.currency.application.functional_currency.dto.functional_currency_period_dto import (
    FunctionalCurrencyPeriodDTO,
)
from src.modules.currency.application.functional_currency.query.list_functional_currency_periods_query import (
    ListFunctionalCurrencyPeriodsQuery,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)


class ListFunctionalCurrencyPeriodsUseCase:
    """Execute the list functional currency periods read scenario."""

    def __init__(self, repository: FunctionalCurrencyRepository):
        self.repository = repository

    async def __call__(
        self, query: ListFunctionalCurrencyPeriodsQuery
    ) -> tuple[FunctionalCurrencyPeriodDTO, ...]:
        return tuple(
            FunctionalCurrencyPeriodDTO.from_entity(p)
            for p in await self.repository.list_periods(tenant_id=query.tenant_id)
        )


__all__ = ["ListFunctionalCurrencyPeriodsUseCase"]
