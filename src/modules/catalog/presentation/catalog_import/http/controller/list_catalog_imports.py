from dataclasses import asdict
from typing import Annotated
from fastapi import Query
from src.modules.catalog.presentation.catalog_import.depends import (
    ListCatalogImportsHandlerDep,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_imports.query import (
    ListCatalogImportsQuery,
)
from src.modules.catalog.presentation.catalog_import.http.response.list_catalog_imports import (
    ListCatalogImportsResponse,
)
from src.modules.catalog.presentation.catalog_import.http.response.get_catalog_import import (
    CatalogImportSummaryResponse,
)


async def list_catalog_imports(
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogImportsHandlerDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListCatalogImportsResponse:
    """Читает одну страницу журнала текущего tenant."""
    result = await handler.execute(ListCatalogImportsQuery(offset, limit))
    return ListCatalogImportsResponse(
        items=[CatalogImportSummaryResponse(**asdict(item)) for item in result.items],
        total=result.total,
    )
