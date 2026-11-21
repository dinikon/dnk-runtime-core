from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_document.http.controller.create_issue_draft import (
    create_issue_draft,
)
from src.modules.inventory.presentation.stock_document.http.response.create_issue_draft import (
    CreateIssueDraftResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_issue_documents import (
    list_issue_documents,
)
from src.modules.inventory.presentation.stock_document.http.response.list_issue_documents import (
    ListIssueDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_issue_document import (
    get_issue_document,
)
from src.modules.inventory.presentation.stock_document.http.response.get_issue_document import (
    GetIssueDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.patch_issue_document import (
    patch_issue_document,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_issue_document import (
    PatchIssueDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.confirm_issue_document import (
    confirm_issue_document,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_issue_document import (
    ConfirmIssueDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.cancel_issue_document import (
    cancel_issue_document,
)
from src.modules.inventory.presentation.stock_document.http.response.cancel_issue_document import (
    CancelIssueDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.post_issue import (
    post_issue,
)
from src.modules.inventory.presentation.stock_document.http.response.post_issue import (
    PostIssueResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.prepare_issue import (
    prepare_issue,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_issue import (
    PrepareIssueResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_issue_sources import (
    list_issue_sources,
)
from src.modules.inventory.presentation.stock_document.http.response.list_issue_sources import (
    ListIssueSourcesResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_issue_executions import (
    list_issue_executions,
)
from src.modules.inventory.presentation.stock_document.http.response.list_issue_executions import (
    ListIssueExecutionsResponse,
)

router = APIRouter(
    prefix="/issues",
    tags=["inventory-stock-issues"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_issue_draft,
    methods=["POST"],
    response_model=CreateIssueDraftResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_issue_documents,
    methods=["GET"],
    response_model=ListIssueDocumentsResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    get_issue_document,
    methods=["GET"],
    response_model=GetIssueDocumentResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    patch_issue_document,
    methods=["PATCH"],
    response_model=PatchIssueDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/confirm",
    confirm_issue_document,
    methods=["POST"],
    response_model=ConfirmIssueDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/cancel",
    cancel_issue_document,
    methods=["POST"],
    response_model=CancelIssueDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/issue",
    post_issue,
    methods=["POST"],
    response_model=PostIssueResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/issue-context",
    prepare_issue,
    methods=["GET"],
    response_model=PrepareIssueResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/source-positions",
    list_issue_sources,
    methods=["GET"],
    response_model=ListIssueSourcesResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/executions",
    list_issue_executions,
    methods=["GET"],
    response_model=ListIssueExecutionsResponse,
    status_code=200,
)
