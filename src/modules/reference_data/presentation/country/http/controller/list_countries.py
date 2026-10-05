from src.modules.reference_data.application.country.query.list_countries.handler import (
    ListCountriesHandler,
)
from src.modules.reference_data.application.country.query.list_countries.query import (
    ListCountriesQuery,
)
from src.modules.reference_data.presentation.country.http.response.country import (
    CountryResponse,
)
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep


async def list_countries(repository: CatalogRepositoryDep) -> list[CountryResponse]:
    records = await ListCountriesHandler(repository).execute(ListCountriesQuery())
    return [
        CountryResponse(
            code=r.code, alpha3=r.alpha3, numeric_code=r.numeric_code, name=r.name
        )
        for r in records
    ]
