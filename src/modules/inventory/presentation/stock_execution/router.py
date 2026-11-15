from fastapi import APIRouter,Depends
from src.modules.identity.presentation.auth.depends import require_authenticated_request_context
from src.modules.inventory.presentation.stock_execution.http.controller.get_stock_execution import get_stock_execution
from src.modules.inventory.presentation.stock_execution.http.response.get_stock_execution import GetStockExecutionResponse
router=APIRouter(prefix="/inventory/stock-executions",tags=["inventory-stock-executions"],dependencies=[Depends(require_authenticated_request_context)])
router.add_api_route("/{identifier}",get_stock_execution,methods=["GET"],response_model=GetStockExecutionResponse)
