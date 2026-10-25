from uuid import UUID
from src.modules.catalog.presentation.catalog_import.depends import (
    ConfigureCatalogImportHandlerDep,
    import_http_error,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.catalog.domain.error import CatalogError
from src.modules.catalog.application.catalog_import.command.configure_catalog_import.command import (
    ConfigureCatalogImportCommand,
)
from src.modules.catalog.presentation.catalog_import.http.response.configure_catalog_import import (
    ConfigureCatalogImportResponse,
)
from src.modules.catalog.presentation.catalog_import.http.request.configure_catalog_import import (
    ConfigureCatalogImportRequest,
)


async def configure_catalog_import(
    import_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ConfigureCatalogImportHandlerDep,
    payload: ConfigureCatalogImportRequest,
) -> ConfigureCatalogImportResponse:
    """Выполняет отдельный HTTP-сценарий configure_catalog_import."""
    try:
        result = await handler.execute(
            ConfigureCatalogImportCommand(import_id, payload.to_configuration())
        )
        return ConfigureCatalogImportResponse(
            id=result.id, version=result.version, status=result.status
        )
    except CatalogError as error:
        raise import_http_error(error) from error
