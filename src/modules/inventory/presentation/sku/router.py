from fastapi import APIRouter, Depends

from src.modules.inventory.presentation.sku.http.controller.create_sku import create_sku
from src.modules.inventory.presentation.sku.http.controller.get_sku import get_sku
from src.modules.inventory.presentation.sku.http.controller.list_skus import list_skus
from src.modules.inventory.presentation.sku.http.response.create_sku import (
    CreateSkuResponse,
)
from src.modules.inventory.presentation.sku.http.response.get_sku import GetSkuResponse
from src.modules.inventory.presentation.sku.http.response.list_skus import (
    ListSkuItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/inventory/skus", tags=["inventory-skus"])
router.add_api_route(
    "",
    create_sku,
    methods=["POST"],
    status_code=201,
    response_model=CreateSkuResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_skus,
    methods=["GET"],
    response_model=list[ListSkuItemResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{sku_id}",
    get_sku,
    methods=["GET"],
    response_model=GetSkuResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
