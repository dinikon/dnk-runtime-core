from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.application.time_zone.query.list_time_zones.query import (
    ListTimeZonesQuery,
)
from src.modules.reference_data.domain.time_zone.record import TimeZone


class ListTimeZonesHandler:
    def __init__(self, repository: CatalogRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, query: ListTimeZonesQuery) -> list[TimeZone]:
        return await self._repository.list_time_zones()
