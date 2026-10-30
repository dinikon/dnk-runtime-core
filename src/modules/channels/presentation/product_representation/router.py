from fastapi import APIRouter, Depends

from src.modules.channels.presentation.catalog_binding.http.route import BindingRoute
from src.modules.channels.presentation.product_representation.http.controller.preview_representation import (
    preview_representation,
)
from src.modules.channels.presentation.product_representation.http.response.preview_representation import (
    PreviewRepresentationResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(
    prefix="/channels", tags=["product-representations"], route_class=BindingRoute
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/representation/preview",
    preview_representation,
    methods=["POST"],
    response_model=PreviewRepresentationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
