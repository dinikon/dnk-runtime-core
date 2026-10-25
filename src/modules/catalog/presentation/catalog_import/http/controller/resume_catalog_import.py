from uuid import UUID
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.presentation.catalog_import.depends import (
    ResumeCatalogImportHandlerDep,
    import_http_error,
)
from src.modules.catalog.application.catalog_import.command.resume_catalog_import.command import (
    ResumeCatalogImportCommand,
)
from src.modules.catalog.presentation.catalog_import.http.request.resume_catalog_import import (
    ResumeCatalogImportRequest,
)
from src.modules.catalog.presentation.catalog_import.http.response.resume_catalog_import import (
    ResumeCatalogImportResponse,
)
from src.modules.catalog.domain.error import CatalogError


async def resume_catalog_import(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ResumeCatalogImportHandlerDep,
    payload: ResumeCatalogImportRequest,
) -> ResumeCatalogImportResponse:
    """Продолжает подготовленный остановленный запуск в доверенном tenant."""
    try:
        result = await handler.execute(
            ResumeCatalogImportCommand(import_id, payload.generation)
        )
        return ResumeCatalogImportResponse(
            id=result.id, status=result.status, generation=result.generation
        )
    except CatalogError as error:
        raise import_http_error(error) from error
