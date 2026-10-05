from src.modules.reference_data.application.currency.query.list_currencies.handler import (
    ListCurrenciesHandler,
)
from src.modules.reference_data.application.currency.query.list_currencies.query import (
    ListCurrenciesQuery,
)
from src.modules.reference_data.presentation.currency.http.response.currency import (
    CurrencyResponse,
)
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep


async def list_currencies(repository: CatalogRepositoryDep) -> list[CurrencyResponse]:
    records = await ListCurrenciesHandler(repository).execute(ListCurrenciesQuery())
    return [
        CurrencyResponse(
            code=r.code,
            numeric_code=r.numeric_code,
            name=r.name,
            minor_units=r.minor_units,
        )
        for r in records
    ]
