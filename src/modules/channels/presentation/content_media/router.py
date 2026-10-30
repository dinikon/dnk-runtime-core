from fastapi import APIRouter, Depends
from src.modules.channels.presentation.content_media.http.controller.get_media_head import (
    get_media_head,
)

from src.modules.channels.presentation.content_media.http.route import ContentMediaRoute
from src.modules.channels.presentation.content_media.http.controller.prepare_gallery import (
    prepare_gallery,
)
from src.modules.channels.presentation.content_media.http.controller.revoke_media_access import (
    revoke_media_access,
)
from src.modules.channels.presentation.content_media.http.controller.renew_media_access import (
    renew_media_access,
)
from src.modules.channels.presentation.content_media.http.controller.get_media_content import (
    get_media_content,
)
from src.modules.channels.presentation.content_media.http.response.prepare_gallery import (
    PrepareGalleryResponse,
)
from src.modules.channels.presentation.content_media.http.response.revoke_media_access import (
    RevokeMediaAccessResponse,
)
from src.modules.channels.presentation.content_media.http.response.renew_media_access import (
    RenewMediaAccessResponse,
)
from src.modules.channels.presentation.http.transaction import prepare_channels_read
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(
    prefix="/channels",
    tags=["content-media"],
    route_class=ContentMediaRoute,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/representation/gallery/prepare",
    prepare_gallery,
    methods=["POST"],
    response_model=PrepareGalleryResponse,
)
router.add_api_route(
    "/{channel_id}/content-media/{media_id}/revoke",
    revoke_media_access,
    methods=["POST"],
    response_model=RevokeMediaAccessResponse,
)
router.add_api_route(
    "/{channel_id}/content-media/{media_id}/renew",
    renew_media_access,
    methods=["POST"],
    response_model=RenewMediaAccessResponse,
)

public_router = APIRouter(
    prefix="/api/channels/content-media",
    tags=["content-media"],
    route_class=ContentMediaRoute,
    dependencies=[Depends(prepare_channels_read)],
)
public_router.add_api_route(
    "/{media_id}/image.{extension}",
    get_media_content,
    methods=["GET"],
    response_model=None,
    responses={
        200: {
            "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}
        }
    },
)
public_router.add_api_route(
    "/{media_id}/image.{extension}",
    get_media_head,
    methods=["HEAD"],
    response_model=None,
)
