from src.modules.reference_data.application.locale.query.list_locales.query import (
    ListLocalesQuery,
)
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.domain.locale.record import Locale


class ListLocalesHandler:
    def __init__(self, repository: CatalogRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, query: ListLocalesQuery) -> list[Locale]:
        return await self._repository.list_locales()
