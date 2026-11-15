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
router.add_api_route(
    "/{document_id}",
    get_receipt_document,
    methods=["GET"],
    response_model=GetReceiptDocumentResponse,
)
