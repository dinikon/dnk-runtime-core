from src.modules.reference_data.application.time_zone.query.list_time_zones.handler import (
    ListTimeZonesHandler,
)
from src.modules.reference_data.application.time_zone.query.list_time_zones.query import (
    ListTimeZonesQuery,
)
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep
from src.modules.reference_data.presentation.time_zone.http.response.time_zone import (
    TimeZoneResponse,
)


async def list_time_zones(repository: CatalogRepositoryDep) -> list[TimeZoneResponse]:
    records = await ListTimeZonesHandler(repository).execute(ListTimeZonesQuery())
    return [
        TimeZoneResponse(code=r.code, country_codes=list(r.country_codes))
        for r in records
    ]
