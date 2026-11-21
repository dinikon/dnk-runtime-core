from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_document.http.controller.create_return_draft import (
    create_return_draft,
)
from src.modules.inventory.presentation.stock_document.http.response.create_return_draft import (
    CreateReturnDraftResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_return_documents import (
    list_return_documents,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_documents import (
    ListReturnDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_return_document import (
    get_return_document,
)
from src.modules.inventory.presentation.stock_document.http.response.get_return_document import (
    GetReturnDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.patch_return_document import (
    patch_return_document,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_return_document import (
    PatchReturnDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.confirm_return_document import (
    confirm_return_document,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_return_document import (
    ConfirmReturnDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.cancel_return_document import (
    cancel_return_document,
)
from src.modules.inventory.presentation.stock_document.http.response.cancel_return_document import (
    CancelReturnDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.post_return import (
    post_return,
)
from src.modules.inventory.presentation.stock_document.http.response.post_return import (
    PostReturnResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.prepare_return import (
    prepare_return,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_return import (
    PrepareReturnResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_return_sources import (
    list_return_sources,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_sources import (
    ListReturnSourcesResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_return_executions import (
    list_return_executions,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_executions import (
    ListReturnExecutionsResponse,
)

router = APIRouter(
    prefix="/returns",
    tags=["inventory-stock-returns"],
    dependencies=[Depends(require_authenticated_request_context)],
)

router.add_api_route(
    "",
    create_return_draft,
    methods=["POST"],
    response_model=CreateReturnDraftResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_return_documents,
    methods=["GET"],
    response_model=ListReturnDocumentsResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    get_return_document,
    methods=["GET"],
    response_model=GetReturnDocumentResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    patch_return_document,
    methods=["PATCH"],
    response_model=PatchReturnDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/confirm",
    confirm_return_document,
    methods=["POST"],
    response_model=ConfirmReturnDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/cancel",
    cancel_return_document,
    methods=["POST"],
    response_model=CancelReturnDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/return",
    post_return,
    methods=["POST"],
    response_model=PostReturnResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/return-context",
    prepare_return,
    methods=["GET"],
    response_model=PrepareReturnResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/source-positions",
    list_return_sources,
    methods=["GET"],
    response_model=ListReturnSourcesResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/executions",
    list_return_executions,
    methods=["GET"],
    response_model=ListReturnExecutionsResponse,
    status_code=200,
)

from src.modules.inventory.presentation.stock_document.http.controller.preview_return import (
    preview_return,
)
from src.modules.inventory.presentation.stock_document.http.response.preview_return import (
    PreviewReturnResponse,
)

router.add_api_route(
    "/{document_id}/preview",
    preview_return,
    methods=["POST"],
    response_model=PreviewReturnResponse,
    dependencies=[Depends(require_csrf)],
)

from src.modules.inventory.presentation.stock_document.http.controller.list_return_destinations import (
    list_return_destinations,
)
from src.modules.inventory.presentation.stock_document.http.response.list_return_destinations import (
    ListReturnDestinationsResponse,
)

router.add_api_route(
    "/{document_id}/destination-locations",
    list_return_destinations,
    methods=["GET"],
    response_model=ListReturnDestinationsResponse,
)
