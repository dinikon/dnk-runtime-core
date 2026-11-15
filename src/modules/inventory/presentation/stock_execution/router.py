from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.inventory.presentation.stock_execution.http.controller.get_stock_execution import (
    get_stock_execution,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_stock_execution import (
    GetStockExecutionResponse,
)

router = APIRouter(
    prefix="/inventory/stock-executions",
    tags=["inventory-stock-executions"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{identifier}",
    get_stock_execution,
    methods=["GET"],
    response_model=GetStockExecutionResponse,
)

from src.modules.inventory.presentation.stock_execution.http.controller.list_stock_executions import (
    list_stock_executions,
)
from src.modules.inventory.presentation.stock_execution.http.response.list_stock_executions import (
    ListStockExecutionsResponse,
)

router.add_api_route(
    "",
    list_stock_executions,
    methods=["GET"],
    response_model=ListStockExecutionsResponse,
)

from src.modules.inventory.presentation.stock_execution.http.controller.get_stock_execution_details import (
    get_stock_execution_details,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_stock_execution_details import (
    GetStockExecutionDetailsResponse,
)

router.add_api_route(
    "/{identifier}/details",
    get_stock_execution_details,
    methods=["GET"],
    response_model=GetStockExecutionDetailsResponse,
)

from src.modules.inventory.presentation.stock_execution.http.controller.get_issue_execution_result import (
    get_issue_execution_result,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_issue_execution_result import (
    GetIssueExecutionResultResponse,
)

router.add_api_route(
    "/{identifier}/issue-result",
    get_issue_execution_result,
    methods=["GET"],
    response_model=GetIssueExecutionResultResponse,
)
