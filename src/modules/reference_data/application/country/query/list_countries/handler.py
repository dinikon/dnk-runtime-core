from src.modules.reference_data.application.country.query.list_countries.query import (
    ListCountriesQuery,
)
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.domain.country.record import Country


class ListCountriesHandler:
    def __init__(self, repository: CatalogRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, query: ListCountriesQuery) -> list[Country]:
        return await self._repository.list_countries()
