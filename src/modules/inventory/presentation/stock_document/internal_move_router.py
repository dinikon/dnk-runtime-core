from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.stock_document.http.controller.create_internal_move_draft import (
    create_internal_move_draft,
)
from src.modules.inventory.presentation.stock_document.http.response.create_internal_move_draft import (
    CreateInternalMoveDraftResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_internal_move_documents import (
    list_internal_move_documents,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_documents import (
    ListInternalMoveDocumentsResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.get_internal_move_document import (
    get_internal_move_document,
)
from src.modules.inventory.presentation.stock_document.http.response.get_internal_move_document import (
    GetInternalMoveDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.patch_internal_move_document import (
    patch_internal_move_document,
)
from src.modules.inventory.presentation.stock_document.http.response.patch_internal_move_document import (
    PatchInternalMoveDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.confirm_internal_move_document import (
    confirm_internal_move_document,
)
from src.modules.inventory.presentation.stock_document.http.response.confirm_internal_move_document import (
    ConfirmInternalMoveDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.cancel_internal_move_document import (
    cancel_internal_move_document,
)
from src.modules.inventory.presentation.stock_document.http.response.cancel_internal_move_document import (
    CancelInternalMoveDocumentResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.post_internal_move import (
    post_internal_move,
)
from src.modules.inventory.presentation.stock_document.http.response.post_internal_move import (
    PostInternalMoveResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.prepare_internal_move import (
    prepare_internal_move,
)
from src.modules.inventory.presentation.stock_document.http.response.prepare_internal_move import (
    PrepareInternalMoveResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_internal_move_sources import (
    list_internal_move_sources,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_sources import (
    ListInternalMoveSourcesResponse,
)
from src.modules.inventory.presentation.stock_document.http.controller.list_internal_move_executions import (
    list_internal_move_executions,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_executions import (
    ListInternalMoveExecutionsResponse,
)

router = APIRouter(
    prefix="/internal-moves",
    tags=["inventory-stock-internal-moves"],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_internal_move_draft,
    methods=["POST"],
    response_model=CreateInternalMoveDraftResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_internal_move_documents,
    methods=["GET"],
    response_model=ListInternalMoveDocumentsResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    get_internal_move_document,
    methods=["GET"],
    response_model=GetInternalMoveDocumentResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}",
    patch_internal_move_document,
    methods=["PATCH"],
    response_model=PatchInternalMoveDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/confirm",
    confirm_internal_move_document,
    methods=["POST"],
    response_model=ConfirmInternalMoveDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/cancel",
    cancel_internal_move_document,
    methods=["POST"],
    response_model=CancelInternalMoveDocumentResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/move",
    post_internal_move,
    methods=["POST"],
    response_model=PostInternalMoveResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{document_id}/move-context",
    prepare_internal_move,
    methods=["GET"],
    response_model=PrepareInternalMoveResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/source-positions",
    list_internal_move_sources,
    methods=["GET"],
    response_model=ListInternalMoveSourcesResponse,
    status_code=200,
)
router.add_api_route(
    "/{document_id}/executions",
    list_internal_move_executions,
    methods=["GET"],
    response_model=ListInternalMoveExecutionsResponse,
    status_code=200,
)

from src.modules.inventory.presentation.stock_document.http.controller.list_internal_move_destinations import (
    list_internal_move_destinations,
)
from src.modules.inventory.presentation.stock_document.http.response.list_internal_move_destinations import (
    ListInternalMoveDestinationsResponse,
)

router.add_api_route(
    "/{document_id}/destination-locations",
    list_internal_move_destinations,
    methods=["GET"],
    response_model=ListInternalMoveDestinationsResponse,
)
