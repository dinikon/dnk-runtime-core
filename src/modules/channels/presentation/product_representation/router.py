from fastapi import APIRouter, Depends

from src.modules.channels.presentation.product_representation.http.route import (
    RepresentationRoute,
)
from src.modules.channels.presentation.product_representation.http.controller.get_representation import (
    get_representation,
)
from src.modules.channels.presentation.product_representation.http.response.get_representation import (
    GetRepresentationResponse,
)
from src.modules.channels.presentation.product_representation.http.controller.save_representation import (
    save_representation,
)
from src.modules.channels.presentation.product_representation.http.response.save_representation import (
    SaveRepresentationResponse,
)
from src.modules.channels.presentation.product_representation.http.controller.enable_representation_export import (
    enable_representation_export,
)
from src.modules.channels.presentation.product_representation.http.response.enable_representation_export import (
    EnableRepresentationExportResponse,
)
from src.modules.channels.presentation.product_representation.http.controller.disable_representation_export import (
    disable_representation_export,
)
from src.modules.channels.presentation.product_representation.http.response.disable_representation_export import (
    DisableRepresentationExportResponse,
)
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
    prefix="/channels",
    tags=["product-representations"],
    route_class=RepresentationRoute,
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

router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/representation",
    get_representation,
    methods=["GET"],
    response_model=GetRepresentationResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/representation",
    save_representation,
    methods=["PUT"],
    response_model=SaveRepresentationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/representation/enable",
    enable_representation_export,
    methods=["POST"],
    response_model=EnableRepresentationExportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/representation/disable",
    disable_representation_export,
    methods=["POST"],
    response_model=DisableRepresentationExportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
