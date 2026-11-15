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
