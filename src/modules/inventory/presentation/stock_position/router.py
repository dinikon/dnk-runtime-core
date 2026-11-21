from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)

router = APIRouter(
    prefix="/inventory/stock-positions",
    tags=["inventory-stock-positions"],
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.inventory.presentation.stock_position.http.controller.list_stock_positions import (
    list_stock_positions,
)
from src.modules.inventory.presentation.stock_position.http.response.list_stock_positions import (
    ListStockPositionsResponse,
)

router.add_api_route(
    "", list_stock_positions, methods=["GET"], response_model=ListStockPositionsResponse
)

from src.modules.inventory.presentation.stock_position.http.controller.get_stock_position import (
    get_stock_position,
)
from src.modules.inventory.presentation.stock_position.http.response.get_stock_position import (
    GetStockPositionResponse,
)

router.add_api_route(
    "/{identifier}",
    get_stock_position,
    methods=["GET"],
    response_model=GetStockPositionResponse,
)

from src.modules.inventory.presentation.stock_position.http.controller.list_stock_balances import (
    list_stock_balances,
)
from src.modules.inventory.presentation.stock_position.http.response.list_stock_balances import (
    ListStockBalancesResponse,
)

balances_router = APIRouter(
    prefix="/inventory/stock-balances",
    tags=["inventory-stock-balances"],
    dependencies=[Depends(require_authenticated_request_context)],
)
balances_router.add_api_route(
    "", list_stock_balances, methods=["GET"], response_model=ListStockBalancesResponse
)
