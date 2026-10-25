from uuid import UUID
from src.modules.catalog.presentation.catalog_import.depends import (
    StartCatalogImportHandlerDep,
    import_http_error,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.domain.error import CatalogError
from src.modules.catalog.application.catalog_import.command.start_catalog_import.command import (
    StartCatalogImportCommand,
)
from src.modules.catalog.presentation.catalog_import.http.response.start_catalog_import import (
    StartCatalogImportResponse,
)
from src.modules.catalog.presentation.catalog_import.http.request.start_catalog_import import (
    StartCatalogImportRequest,
)


async def start_catalog_import(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: StartCatalogImportHandlerDep,
    payload: StartCatalogImportRequest,
) -> StartCatalogImportResponse:
    """Выполняет отдельный HTTP-сценарий start_catalog_import."""
    try:
        result = await handler.execute(
            StartCatalogImportCommand(import_id, payload.version)
        )
        return StartCatalogImportResponse(id=result.id, status=result.status)
    except CatalogError as error:
        raise import_http_error(error) from error
