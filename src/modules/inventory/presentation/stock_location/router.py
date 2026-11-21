from fastapi import APIRouter, Depends

from src.modules.inventory.presentation.stock_location.http.controller.put_stock_location import (
    put_stock_location,
)
from src.modules.inventory.presentation.stock_location.http.controller.patch_stock_location import (
    patch_stock_location,
)
from src.modules.inventory.presentation.stock_location.http.response.put_stock_location import (
    PutStockLocationResponse,
)
from src.modules.inventory.presentation.stock_location.http.response.patch_stock_location import (
    PatchStockLocationResponse,
)

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_location.http.controller.create_stock_location import (
    create_stock_location,
)
from src.modules.inventory.presentation.stock_location.http.controller.get_stock_location import (
    get_stock_location,
)
from src.modules.inventory.presentation.stock_location.http.controller.list_stock_locations import (
    list_stock_locations,
)
from src.modules.inventory.presentation.stock_location.http.response.create_stock_location import (
    CreateStockLocationResponse,
)
from src.modules.inventory.presentation.stock_location.http.response.get_stock_location import (
    GetStockLocationResponse,
)
from src.modules.inventory.presentation.stock_location.http.response.list_stock_locations import (
    ListStockLocationsResponse,
)

router = APIRouter(
    prefix="/inventory/warehouses/{warehouse_id}/locations",
    tags=["inventory-stock-locations"],
)
router.add_api_route(
    "/{location_id}",
    put_stock_location,
    methods=["PUT"],
    response_model=PutStockLocationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{location_id}",
    patch_stock_location,
    methods=["PATCH"],
    response_model=PatchStockLocationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    create_stock_location,
    methods=["POST"],
    status_code=201,
    response_model=CreateStockLocationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_stock_locations,
    methods=["GET"],
    response_model=ListStockLocationsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{location_id}",
    get_stock_location,
    methods=["GET"],
    response_model=GetStockLocationResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
