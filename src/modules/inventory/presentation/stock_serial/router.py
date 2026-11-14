from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_serial.http.controller.create_stock_serial import (
    create_stock_serial,
)
from src.modules.inventory.presentation.stock_serial.http.controller.get_stock_serial import (
    get_stock_serial,
)
from src.modules.inventory.presentation.stock_serial.http.controller.list_stock_serials import (
    list_stock_serials,
)
from src.modules.inventory.presentation.stock_serial.http.response.create_stock_serial import (
    CreateStockSerialResponse,
)
from src.modules.inventory.presentation.stock_serial.http.response.get_stock_serial import (
    GetStockSerialResponse,
)
from src.modules.inventory.presentation.stock_serial.http.response.list_stock_serials import (
    ListStockSerialsResponse,
)

router = APIRouter(
    prefix="/inventory/items/{inventory_item_id}/serials",
    tags=["inventory-stock-serials"],
)
router.add_api_route(
    "",
    create_stock_serial,
    methods=["POST"],
    status_code=201,
    response_model=CreateStockSerialResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_stock_serials,
    methods=["GET"],
    response_model=ListStockSerialsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{serial_id}",
    get_stock_serial,
    methods=["GET"],
    response_model=GetStockSerialResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
