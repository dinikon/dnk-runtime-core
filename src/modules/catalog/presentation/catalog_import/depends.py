from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
)
from src.modules.catalog.infrastructure.catalog_import.repository import (
    SqlAlchemyCatalogImportRepository,
    SqlAlchemyImportRead,
)
from src.modules.catalog.presentation.catalog_import.assembly import build_import_queue
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator


def import_tenant(context: AuthenticatedRequestContextDep) -> UUID:
    """Получает tenant только из доверенного контекста Identity."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    return UUID(context.principal.tenant_id)


ImportTenantDep = Annotated[UUID, Depends(import_tenant)]


def import_http_error(error: CatalogError) -> HTTPException:
    """Преобразует ожидаемую ошибку в конкретный HTTP-ответ."""
    status = (
        404
        if isinstance(error, CatalogNotFoundError)
        else 409 if isinstance(error, CatalogConflictError) else 422
    )
    return HTTPException(status, {"message": str(error), "fields": list(error.fields)})


from src.modules.catalog.application.catalog_import.command.create_catalog_import.handler import (
    CreateCatalogImportHandler,
)


def get_create_catalog_import_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> CreateCatalogImportHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return CreateCatalogImportHandler(
        SqlAlchemyCatalogImportRepository(uow.session),
        build_import_queue(uow.session, tenant),
        UtcClock(),
        UUID7Generator(),
    )


CreateCatalogImportHandlerDep = Annotated[
    CreateCatalogImportHandler, Depends(get_create_catalog_import_handler)
]

from src.modules.catalog.application.catalog_import.command.configure_catalog_import.handler import (
    ConfigureCatalogImportHandler,
)


def get_configure_catalog_import_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> ConfigureCatalogImportHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return ConfigureCatalogImportHandler(
        SqlAlchemyCatalogImportRepository(uow.session),
        build_import_queue(uow.session, tenant),
        UtcClock(),
    )


ConfigureCatalogImportHandlerDep = Annotated[
    ConfigureCatalogImportHandler, Depends(get_configure_catalog_import_handler)
]

from src.modules.catalog.application.catalog_import.command.start_catalog_import.handler import (
    StartCatalogImportHandler,
)


def get_start_catalog_import_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> StartCatalogImportHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return StartCatalogImportHandler(
        SqlAlchemyCatalogImportRepository(uow.session),
        build_import_queue(uow.session, tenant),
        UtcClock(),
    )


StartCatalogImportHandlerDep = Annotated[
    StartCatalogImportHandler, Depends(get_start_catalog_import_handler)
]

from src.modules.catalog.application.catalog_import.command.cancel_catalog_import.handler import (
    CancelCatalogImportHandler,
)


def get_cancel_catalog_import_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> CancelCatalogImportHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return CancelCatalogImportHandler(
        SqlAlchemyCatalogImportRepository(uow.session), UtcClock()
    )


CancelCatalogImportHandlerDep = Annotated[
    CancelCatalogImportHandler, Depends(get_cancel_catalog_import_handler)
]

from src.modules.catalog.application.catalog_import.query.get_catalog_import.handler import (
    GetCatalogImportHandler,
)


def get_get_catalog_import_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> GetCatalogImportHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return GetCatalogImportHandler(SqlAlchemyImportRead(uow.session))


GetCatalogImportHandlerDep = Annotated[
    GetCatalogImportHandler, Depends(get_get_catalog_import_handler)
]

from src.modules.catalog.application.catalog_import.query.list_catalog_imports.handler import (
    ListCatalogImportsHandler,
)


def get_list_catalog_imports_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> ListCatalogImportsHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return ListCatalogImportsHandler(SqlAlchemyImportRead(uow.session))


ListCatalogImportsHandlerDep = Annotated[
    ListCatalogImportsHandler, Depends(get_list_catalog_imports_handler)
]

from src.modules.catalog.application.catalog_import.query.list_catalog_import_rows.handler import (
    ListCatalogImportRowsHandler,
)


def get_list_catalog_import_rows_handler(
    uow: UoWDep, tenant: ImportTenantDep
) -> ListCatalogImportRowsHandler:
    """Собирает конкретный сценарий на общем tenant UoW."""
    return ListCatalogImportRowsHandler(SqlAlchemyImportRead(uow.session))


ListCatalogImportRowsHandlerDep = Annotated[
    ListCatalogImportRowsHandler, Depends(get_list_catalog_import_rows_handler)
]
