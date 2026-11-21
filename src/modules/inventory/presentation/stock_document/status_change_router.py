from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_document.http.controller.create_status_change_draft import (
    create_status_change_draft,
)
from src.modules.inventory.presentation.stock_document.http.response.create_status_change_draft import (
    CreateStatusChangeDraftResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_status_change_documents import (
    list_status_change_documents,
)
from src.modules.inventory.presentation.stock_document.http.response.list_status_change_documents import (
    ListStatusChangeDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_status_change_document import (
    get_status_change_document,
)
from src.modules.inventory.presentation.stock_document.http.response.get_status_change_document import (
    GetStatusChangeDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.patch_status_change_document import (
    patch_status_change_document,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_status_change_document import (
    PatchStatusChangeDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.confirm_status_change_document import (
    confirm_status_change_document,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_status_change_document import (
    ConfirmStatusChangeDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.cancel_status_change_document import (
    cancel_status_change_document,
)
from src.modules.inventory.presentation.stock_document.http.response.cancel_status_change_document import (
    CancelStatusChangeDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.post_status_change import (
    post_status_change,
)
from src.modules.inventory.presentation.stock_document.http.response.post_status_change import (
    PostStatusChangeResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.prepare_status_change import (
    prepare_status_change,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_status_change import (
    PrepareStatusChangeResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_status_change_sources import (
    list_status_change_sources,
)
from src.modules.inventory.presentation.stock_document.http.response.list_status_change_sources import (
    ListStatusChangeSourcesResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_status_change_executions import (
    list_status_change_executions,
)
from src.modules.inventory.presentation.stock_document.http.response.list_status_change_executions import (
    ListStatusChangeExecutionsResponse,
)

router = APIRouter(
    prefix="/status-changes",
    tags=["inventory-stock-status_changes"],
    dependencies=[Depends(require_authenticated_request_context)],
)
from src.modules.inventory.presentation.stock_document.http.controller.get_status_transitions import (
    get_status_transitions,
)
from src.modules.inventory.presentation.stock_document.http.response.get_status_transitions import (
    GetStatusTransitionsResponse,
)

router.add_api_route(
    "/transitions",
    get_status_transitions,
    methods=["GET"],
    response_model=GetStatusTransitionsResponse,
)

router.add_api_route(
    "",
    create_status_change_draft,
    methods=["POST"],
    response_model=CreateStatusChangeDraftResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_status_change_documents,
    methods=["GET"],
    response_model=ListStatusChangeDocumentsResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    get_status_change_document,
    methods=["GET"],
    response_model=GetStatusChangeDocumentResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    patch_status_change_document,
    methods=["PATCH"],
    response_model=PatchStatusChangeDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/confirm",
    confirm_status_change_document,
    methods=["POST"],
    response_model=ConfirmStatusChangeDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/cancel",
    cancel_status_change_document,
    methods=["POST"],
    response_model=CancelStatusChangeDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/change-status",
    post_status_change,
    methods=["POST"],
    response_model=PostStatusChangeResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/status-change-context",
    prepare_status_change,
    methods=["GET"],
    response_model=PrepareStatusChangeResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/source-positions",
    list_status_change_sources,
    methods=["GET"],
    response_model=ListStatusChangeSourcesResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/executions",
    list_status_change_executions,
    methods=["GET"],
    response_model=ListStatusChangeExecutionsResponse,
    status_code=200,
)

from src.modules.inventory.presentation.stock_document.http.controller.preview_status_change import (
    preview_status_change,
)
from src.modules.inventory.presentation.stock_document.http.response.preview_status_change import (
    PreviewStatusChangeResponse,
)

router.add_api_route(
    "/{document_id}/preview",
    preview_status_change,
    methods=["POST"],
    response_model=PreviewStatusChangeResponse,
    dependencies=[Depends(require_csrf)],
)
