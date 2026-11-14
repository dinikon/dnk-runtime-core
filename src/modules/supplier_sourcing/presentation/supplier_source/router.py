from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.supplier_sourcing.presentation.supplier_source.http.controller.create_supplier_source import (
    create_supplier_source,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.create_supplier_source import (
    CreateSupplierSourceResponse,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.controller.list_supplier_sources import (
    list_supplier_sources,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.list_supplier_sources import (
    ListSupplierSourcesResponse,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.controller.get_supplier_source import (
    get_supplier_source,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.get_supplier_source import (
    GetSupplierSourceResponse,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.controller.put_supplier_source import (
    put_supplier_source,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.put_supplier_source import (
    PutSupplierSourceResponse,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.controller.patch_supplier_source import (
    patch_supplier_source,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.patch_supplier_source import (
    PatchSupplierSourceResponse,
)

router = APIRouter(prefix="/supplier-sourcing/sources", tags=["supplier-sources"])
router.add_api_route(
    "",
    create_supplier_source,
    methods=["POST"],
    response_model=CreateSupplierSourceResponse,
    status_code=201,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_supplier_sources,
    methods=["GET"],
    response_model=ListSupplierSourcesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{source_id}",
    get_supplier_source,
    methods=["GET"],
    response_model=GetSupplierSourceResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{source_id}",
    put_supplier_source,
    methods=["PUT"],
    response_model=PutSupplierSourceResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{source_id}",
    patch_supplier_source,
    methods=["PATCH"],
    response_model=PatchSupplierSourceResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
