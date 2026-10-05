from src.modules.reference_data.application.currency.query.list_currencies.query import (
    ListCurrenciesQuery,
)
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.domain.currency.record import Currency


class ListCurrenciesHandler:
    def __init__(self, repository: CatalogRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, query: ListCurrenciesQuery) -> list[Currency]:
        return await self._repository.list_currencies()
