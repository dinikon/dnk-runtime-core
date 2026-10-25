from dataclasses import asdict
from uuid import UUID
from src.modules.catalog.presentation.catalog_import.depends import (
    GetCatalogImportHandlerDep,
    import_http_error,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.application.catalog_import.query.get_catalog_import.query import (
    GetCatalogImportQuery,
)
from src.modules.catalog.presentation.catalog_import.http.response.get_catalog_import import (
    GetCatalogImportResponse,
    CatalogImportSummaryResponse,
    ImportConfigurationResponse,
    ImportAnalysisResponse,
)
from src.modules.catalog.domain.error import CatalogError


async def get_catalog_import(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetCatalogImportHandlerDep,
) -> GetCatalogImportResponse:
    """Явно преобразует DTO чтения в собственные HTTP-схемы."""
    try:
        result = await handler.execute(GetCatalogImportQuery(import_id))
        return GetCatalogImportResponse(
            run=CatalogImportSummaryResponse(**asdict(result.run)),
            configuration=ImportConfigurationResponse(**asdict(result.configuration)),
            analysis=ImportAnalysisResponse(**asdict(result.analysis)),
        )
    except CatalogError as error:
        raise import_http_error(error) from error
