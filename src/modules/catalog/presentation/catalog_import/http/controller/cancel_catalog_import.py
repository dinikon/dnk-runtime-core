from uuid import UUID
from src.modules.catalog.presentation.catalog_import.depends import (
    CancelCatalogImportHandlerDep,
    import_http_error,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.domain.error import CatalogError
from src.modules.catalog.application.catalog_import.command.cancel_catalog_import.command import (
    CancelCatalogImportCommand,
)
from src.modules.catalog.presentation.catalog_import.http.response.cancel_catalog_import import (
    CancelCatalogImportResponse,
)


async def cancel_catalog_import(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: CancelCatalogImportHandlerDep,
) -> CancelCatalogImportResponse:
    """Выполняет отдельный HTTP-сценарий cancel_catalog_import."""
    try:
        result = await handler.execute(CancelCatalogImportCommand(import_id))
        return CancelCatalogImportResponse(id=result.id, status=result.status)
    except CatalogError as error:
        raise import_http_error(error) from error
