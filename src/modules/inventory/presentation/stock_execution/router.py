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

from src.modules.inventory.presentation.stock_execution.http.controller.get_internal_move_execution_result import (
    get_internal_move_execution_result,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_internal_move_execution_result import (
    GetInternalMoveExecutionResultResponse,
)

router.add_api_route(
    "/{identifier}/internal-move-result",
    get_internal_move_execution_result,
    methods=["GET"],
    response_model=GetInternalMoveExecutionResultResponse,
)

from src.modules.inventory.presentation.stock_execution.http.controller.get_write_off_execution_result import (
    get_write_off_execution_result,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_write_off_execution_result import (
    GetWriteOffExecutionResultResponse,
)

router.add_api_route(
    "/{identifier}/write-off-result",
    get_write_off_execution_result,
    methods=["GET"],
    response_model=GetWriteOffExecutionResultResponse,
)

from src.modules.inventory.presentation.stock_execution.http.controller.get_status_change_execution_result import (
    get_status_change_execution_result,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_status_change_execution_result import (
    GetStatusChangeExecutionResultResponse,
)

router.add_api_route(
    "/{identifier}/status-change-result",
    get_status_change_execution_result,
    methods=["GET"],
    response_model=GetStatusChangeExecutionResultResponse,
)

from src.modules.inventory.presentation.stock_execution.http.controller.get_return_execution_result import (
    get_return_execution_result,
)
from src.modules.inventory.presentation.stock_execution.http.response.get_return_execution_result import (
    GetReturnExecutionResultResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_return_origin import (
    get_return_origin,
)
from src.modules.inventory.presentation.stock_document.http.response.get_return_origin import (
    GetReturnOriginResponse,
)

router.add_api_route(
    "/{identifier}/return-result",
    get_return_execution_result,
    methods=["GET"],
    response_model=GetReturnExecutionResultResponse,
)
router.add_api_route(
    "/{identifier}/return-context",
    get_return_origin,
    methods=["GET"],
    response_model=GetReturnOriginResponse,
)
