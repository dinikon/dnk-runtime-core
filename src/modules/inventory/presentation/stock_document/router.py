from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_document.http.controller.create_receipt_draft import (
    create_receipt_draft,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_receipt_document import (
    get_receipt_document,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_receipt_documents import (
    list_receipt_documents,
)
from src.modules.inventory.presentation.stock_document.http.response.create_receipt_draft import (
    CreateReceiptDraftResponse,
)
from src.modules.inventory.presentation.stock_document.http.response.get_receipt_document import (
    GetReceiptDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.response.list_receipt_documents import (
    ListReceiptDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.patch_receipt_document import (
    patch_receipt_document,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_receipt_document import (
    PatchReceiptDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.confirm_receipt_document import (
    confirm_receipt_document,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_receipt_document import (
    ConfirmReceiptDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.cancel_receipt_document import (
    cancel_receipt_document,
)
from src.modules.inventory.presentation.stock_document.http.response.cancel_receipt_document import (
    CancelReceiptDocumentResponse,
)

router = APIRouter(
    prefix="/inventory/stock-documents",
    tags=["inventory-stock-documents"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_receipt_draft,
    methods=["POST"],
    response_model=CreateReceiptDraftResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_receipt_documents,
    methods=["GET"],
    response_model=ListReceiptDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.issue_router import (
    router as issue_router,
)

from src.modules.inventory.presentation.stock_document.internal_move_router import (
    router as internal_move_router,
)

router.include_router(internal_move_router)
router.include_router(issue_router)

router.add_api_route(
    "/{document_id}",
    get_receipt_document,
    methods=["GET"],
    response_model=GetReceiptDocumentResponse,
)


router.add_api_route(
    "/{document_id}",
    patch_receipt_document,
    methods=["PATCH"],
    response_model=PatchReceiptDocumentResponse,
    dependencies=[Depends(require_csrf)],
)


router.add_api_route(
    "/{document_id}/confirm",
    confirm_receipt_document,
    methods=["POST"],
    response_model=ConfirmReceiptDocumentResponse,
    dependencies=[Depends(require_csrf)],
)


router.add_api_route(
    "/{document_id}/cancel",
    cancel_receipt_document,
    methods=["POST"],
    response_model=CancelReceiptDocumentResponse,
    dependencies=[Depends(require_csrf)],
)

from src.modules.inventory.presentation.stock_document.http.controller.post_receipt import (
    post_receipt,
)
from src.modules.inventory.presentation.stock_document.http.response.post_receipt import (
    PostReceiptResponse,
)

router.add_api_route(
    "/{document_id}/receive",
    post_receipt,
    methods=["POST"],
    response_model=PostReceiptResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)

from src.modules.inventory.presentation.stock_document.http.controller.prepare_receipt import (
    prepare_receipt,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_receipt import (
    PrepareReceiptResponse,
)

router.add_api_route(
    "/{document_id}/receipt-context",
    prepare_receipt,
    methods=["GET"],
    response_model=PrepareReceiptResponse,
)

from src.modules.inventory.presentation.stock_document.http.controller.list_receipt_executions import (
    list_receipt_executions,
)
from src.modules.inventory.presentation.stock_document.http.response.list_receipt_executions import (
    ListReceiptExecutionsResponse,
)

router.add_api_route(
    "/{document_id}/executions",
    list_receipt_executions,
    methods=["GET"],
    response_model=ListReceiptExecutionsResponse,
)

from src.modules.inventory.presentation.stock_document.http.controller.list_receipt_references import (
    list_receipt_references,
)
from src.modules.inventory.presentation.stock_document.http.response.list_receipt_references import (
    ListReceiptReferencesResponse,
)

router.add_api_route(
    "/{document_id}/receipt-references",
    list_receipt_references,
    methods=["GET"],
    response_model=ListReceiptReferencesResponse,
)
