from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/imports", tags=["catalog-import"])

from src.modules.catalog.presentation.catalog_import.http.controller.create_catalog_import import (
    create_catalog_import,
)
from src.modules.catalog.presentation.catalog_import.http.response.create_catalog_import import (
    CreateCatalogImportResponse,
)
from src.modules.catalog.presentation.catalog_import.http.request.create_catalog_import import (
    CreateCatalogImportRequest,
)

router.add_api_route(
    "",
    create_catalog_import,
    methods=["POST"],
    status_code=202,
    response_model=CreateCatalogImportResponse,
    openapi_extra=CreateCatalogImportRequest.openapi_body(),
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_import.http.controller.list_catalog_imports import (
    list_catalog_imports,
)
from src.modules.catalog.presentation.catalog_import.http.response.list_catalog_imports import (
    ListCatalogImportsResponse,
)

router.add_api_route(
    "",
    list_catalog_imports,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogImportsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.catalog.presentation.catalog_import.http.controller.get_catalog_import import (
    get_catalog_import,
)
from src.modules.catalog.presentation.catalog_import.http.response.get_catalog_import import (
    GetCatalogImportResponse,
)

router.add_api_route(
    "/{import_id}",
    get_catalog_import,
    methods=["GET"],
    status_code=200,
    response_model=GetCatalogImportResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.catalog.presentation.catalog_import.http.controller.configure_catalog_import import (
    configure_catalog_import,
)
from src.modules.catalog.presentation.catalog_import.http.response.configure_catalog_import import (
    ConfigureCatalogImportResponse,
)

router.add_api_route(
    "/{import_id}/configuration",
    configure_catalog_import,
    methods=["PUT"],
    status_code=202,
    response_model=ConfigureCatalogImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_import.http.controller.start_catalog_import import (
    start_catalog_import,
)
from src.modules.catalog.presentation.catalog_import.http.response.start_catalog_import import (
    StartCatalogImportResponse,
)

router.add_api_route(
    "/{import_id}/start",
    start_catalog_import,
    methods=["POST"],
    status_code=202,
    response_model=StartCatalogImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_import.http.controller.cancel_catalog_import import (
    cancel_catalog_import,
)
from src.modules.catalog.presentation.catalog_import.http.response.cancel_catalog_import import (
    CancelCatalogImportResponse,
)

router.add_api_route(
    "/{import_id}/cancel",
    cancel_catalog_import,
    methods=["POST"],
    status_code=202,
    response_model=CancelCatalogImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

from src.modules.catalog.presentation.catalog_import.http.controller.list_catalog_import_rows import (
    list_catalog_import_rows,
)
from src.modules.catalog.presentation.catalog_import.http.response.list_catalog_import_rows import (
    ListCatalogImportRowsResponse,
)

router.add_api_route(
    "/{import_id}/rows",
    list_catalog_import_rows,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogImportRowsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.catalog.presentation.catalog_import.http.controller.export_catalog_import_report import (
    export_catalog_import_report,
)

router.add_api_route(
    "/{import_id}/report.csv",
    export_catalog_import_report,
    methods=["GET"],
    status_code=200,
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}
        }
    },
    dependencies=[Depends(require_authenticated_request_context)],
)
