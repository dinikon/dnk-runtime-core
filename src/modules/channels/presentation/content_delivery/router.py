from fastapi import APIRouter, Depends
from src.modules.channels.presentation.content_delivery.http.route import (
    ContentDeliveryRoute,
)
from src.modules.channels.presentation.content_delivery.http.controller.request_content_delivery import (
    request_content_delivery,
)
from src.modules.channels.presentation.content_delivery.http.controller.get_content_deliveries import (
    get_content_deliveries,
)
from src.modules.channels.presentation.content_delivery.http.controller.request_content_reconciliation import (
    request_content_reconciliation,
)
from src.modules.channels.presentation.content_delivery.http.response.request_content_delivery import (
    RequestContentDeliveryResponse,
)
from src.modules.channels.presentation.content_delivery.http.response.get_content_deliveries import (
    GetContentDeliveriesResponse,
)
from src.modules.channels.presentation.content_delivery.http.response.request_content_reconciliation import (
    RequestContentReconciliationResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(
    prefix="/channels", tags=["content-deliveries"], route_class=ContentDeliveryRoute
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/content-deliveries",
    request_content_delivery,
    methods=["POST"],
    status_code=202,
    response_model=RequestContentDeliveryResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/content-deliveries",
    get_content_deliveries,
    methods=["GET"],
    response_model=GetContentDeliveriesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/content-deliveries/{publication_id}/reconcile",
    request_content_reconciliation,
    methods=["POST"],
    status_code=202,
    response_model=RequestContentReconciliationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
