from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.inventory.presentation.stock_posting.http.controller.get_stock_posting import (
    get_stock_posting,
)
from src.modules.inventory.presentation.stock_posting.http.response.get_stock_posting import (
    GetStockPostingResponse,
)

router = APIRouter(
    prefix="/inventory/stock-postings",
    tags=["inventory-stock-postings"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{identifier}",
    get_stock_posting,
    methods=["GET"],
    response_model=GetStockPostingResponse,
)

movements_router = APIRouter(
    prefix="/inventory/stock-movements",
    tags=["inventory-stock-movements"],
    dependencies=[Depends(require_authenticated_request_context)],
)

from src.modules.inventory.presentation.stock_posting.http.controller.list_stock_movements import (
    list_stock_movements,
)
from src.modules.inventory.presentation.stock_posting.http.response.list_stock_movements import (
    ListStockMovementsResponse,
)

movements_router.add_api_route(
    "", list_stock_movements, methods=["GET"], response_model=ListStockMovementsResponse
)

from src.modules.inventory.presentation.stock_posting.http.controller.list_stock_postings import (
    list_stock_postings,
)
from src.modules.inventory.presentation.stock_posting.http.response.list_stock_postings import (
    ListStockPostingsResponse,
)

router.add_api_route(
    "", list_stock_postings, methods=["GET"], response_model=ListStockPostingsResponse
)

from src.modules.inventory.presentation.stock_posting.http.controller.get_stock_posting_details import (
    get_stock_posting_details,
)
from src.modules.inventory.presentation.stock_posting.http.response.get_stock_posting_details import (
    GetStockPostingDetailsResponse,
)

router.add_api_route(
    "/{identifier}/details",
    get_stock_posting_details,
    methods=["GET"],
    response_model=GetStockPostingDetailsResponse,
)
