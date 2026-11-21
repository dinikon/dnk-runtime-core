from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_document.http.controller.create_write_off_draft import (
    create_write_off_draft,
)
from src.modules.inventory.presentation.stock_document.http.response.create_write_off_draft import (
    CreateWriteOffDraftResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_write_off_documents import (
    list_write_off_documents,
)
from src.modules.inventory.presentation.stock_document.http.response.list_write_off_documents import (
    ListWriteOffDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_write_off_document import (
    get_write_off_document,
)
from src.modules.inventory.presentation.stock_document.http.response.get_write_off_document import (
    GetWriteOffDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.patch_write_off_document import (
    patch_write_off_document,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_write_off_document import (
    PatchWriteOffDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.confirm_write_off_document import (
    confirm_write_off_document,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_write_off_document import (
    ConfirmWriteOffDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.cancel_write_off_document import (
    cancel_write_off_document,
)
from src.modules.inventory.presentation.stock_document.http.response.cancel_write_off_document import (
    CancelWriteOffDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.post_write_off import (
    post_write_off,
)
from src.modules.inventory.presentation.stock_document.http.response.post_write_off import (
    PostWriteOffResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.prepare_write_off import (
    prepare_write_off,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_write_off import (
    PrepareWriteOffResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_write_off_sources import (
    list_write_off_sources,
)
from src.modules.inventory.presentation.stock_document.http.response.list_write_off_sources import (
    ListWriteOffSourcesResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_write_off_executions import (
    list_write_off_executions,
)
from src.modules.inventory.presentation.stock_document.http.response.list_write_off_executions import (
    ListWriteOffExecutionsResponse,
)

router = APIRouter(
    prefix="/write-offs",
    tags=["inventory-stock-write_offs"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_write_off_draft,
    methods=["POST"],
    response_model=CreateWriteOffDraftResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_write_off_documents,
    methods=["GET"],
    response_model=ListWriteOffDocumentsResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    get_write_off_document,
    methods=["GET"],
    response_model=GetWriteOffDocumentResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    patch_write_off_document,
    methods=["PATCH"],
    response_model=PatchWriteOffDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/confirm",
    confirm_write_off_document,
    methods=["POST"],
    response_model=ConfirmWriteOffDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/cancel",
    cancel_write_off_document,
    methods=["POST"],
    response_model=CancelWriteOffDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/write-off",
    post_write_off,
    methods=["POST"],
    response_model=PostWriteOffResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/write-off-context",
    prepare_write_off,
    methods=["GET"],
    response_model=PrepareWriteOffResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/source-positions",
    list_write_off_sources,
    methods=["GET"],
    response_model=ListWriteOffSourcesResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/executions",
    list_write_off_executions,
    methods=["GET"],
    response_model=ListWriteOffExecutionsResponse,
    status_code=200,
)
