from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_lot.http.controller.create_stock_lot import (
    create_stock_lot,
)
from src.modules.inventory.presentation.stock_lot.http.controller.get_stock_lot import (
    get_stock_lot,
)
from src.modules.inventory.presentation.stock_lot.http.controller.list_stock_lots import (
    list_stock_lots,
)
from src.modules.inventory.presentation.stock_lot.http.response.create_stock_lot import (
    CreateStockLotResponse,
)
from src.modules.inventory.presentation.stock_lot.http.response.get_stock_lot import (
    GetStockLotResponse,
)
from src.modules.inventory.presentation.stock_lot.http.response.list_stock_lots import (
    ListStockLotsResponse,
)

router = APIRouter(
    prefix="/inventory/items/{inventory_item_id}/lots", tags=["inventory-stock-lots"]
)
router.add_api_route(
    "",
    create_stock_lot,
    methods=["POST"],
    status_code=201,
    response_model=CreateStockLotResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_stock_lots,
    methods=["GET"],
    response_model=ListStockLotsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{lot_id}",
    get_stock_lot,
    methods=["GET"],
    response_model=GetStockLotResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
