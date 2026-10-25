from dataclasses import asdict
from typing import Annotated, Literal
from uuid import UUID
from fastapi import Query
from src.modules.catalog.presentation.catalog_import.depends import (
    ListCatalogImportRowsHandlerDep,
    import_http_error,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.application.catalog_import.query.list_catalog_import_rows.query import (
    ListCatalogImportRowsQuery,
)
from src.modules.catalog.presentation.catalog_import.http.response.list_catalog_import_rows import (
    ListCatalogImportRowsResponse,
    CatalogImportRowResponse,
)
from src.modules.catalog.domain.error import CatalogError


async def list_catalog_import_rows(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListCatalogImportRowsHandlerDep,
    outcome: (
        Literal["pending", "created", "updated", "skipped", "errors", "warnings"] | None
    ) = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> ListCatalogImportRowsResponse:
    """Возвращает результаты и предупреждения выбранного запуска."""
    try:
        result = await handler.execute(
            ListCatalogImportRowsQuery(import_id, outcome, offset, limit)
        )
        return ListCatalogImportRowsResponse(
            items=[CatalogImportRowResponse(**asdict(item)) for item in result.items],
            total=result.total,
        )
    except CatalogError as error:
        raise import_http_error(error) from error
