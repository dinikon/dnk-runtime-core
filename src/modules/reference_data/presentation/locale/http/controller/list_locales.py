from src.modules.reference_data.application.locale.query.list_locales.handler import (
    ListLocalesHandler,
)
from src.modules.reference_data.application.locale.query.list_locales.query import (
    ListLocalesQuery,
)
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep
from src.modules.reference_data.presentation.locale.http.response.locale import (
    LocaleResponse,
)


async def list_locales(repository: CatalogRepositoryDep) -> list[LocaleResponse]:
    records = await ListLocalesHandler(repository).execute(ListLocalesQuery())
    return [
        LocaleResponse(
            code=r.code,
            language_code=r.language_code,
            script_code=r.script_code,
            region_code=r.region_code,
            country_code=r.country_code,
            name=r.name,
        )
        for r in records
    ]
