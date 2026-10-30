from fastapi import APIRouter, Depends

from src.modules.channels.presentation.content_feed.http.route import ContentFeedRoute
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http.transaction import prepare_channels_read
from src.modules.channels.presentation.content_feed.http.controller.create_content_feed import (
    create_content_feed,
)
from src.modules.channels.presentation.content_feed.http.response.create_content_feed import (
    CreateContentFeedResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.change_content_feed_source import (
    change_content_feed_source,
)
from src.modules.channels.presentation.content_feed.http.response.change_content_feed_source import (
    ChangeContentFeedSourceResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.enable_content_feed import (
    enable_content_feed,
)
from src.modules.channels.presentation.content_feed.http.response.enable_content_feed import (
    EnableContentFeedResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.disable_content_feed import (
    disable_content_feed,
)
from src.modules.channels.presentation.content_feed.http.response.disable_content_feed import (
    DisableContentFeedResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.rotate_feed_access import (
    rotate_feed_access,
)
from src.modules.channels.presentation.content_feed.http.response.rotate_feed_access import (
    RotateFeedAccessResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.revoke_feed_access import (
    revoke_feed_access,
)
from src.modules.channels.presentation.content_feed.http.response.revoke_feed_access import (
    RevokeFeedAccessResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.get_content_feed import (
    get_content_feed,
)
from src.modules.channels.presentation.content_feed.http.response.get_content_feed import (
    GetContentFeedResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.list_content_feeds import (
    list_content_feeds,
)
from src.modules.channels.presentation.content_feed.http.response.list_content_feeds import (
    ListContentFeedsResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.preview_content_feed import (
    preview_content_feed,
)
from src.modules.channels.presentation.content_feed.http.response.preview_content_feed import (
    PreviewContentFeedResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.delete_content_feed import (
    delete_content_feed,
)
from src.modules.channels.presentation.content_feed.http.controller.get_content_feed_xml import (
    get_content_feed_xml,
)
from src.modules.channels.presentation.content_feed.http.controller.request_feed_import import (
    request_feed_import,
)
from src.modules.channels.presentation.content_feed.http.response.request_feed_import import (
    RequestFeedImportResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.resume_feed_import import (
    resume_feed_import,
)
from src.modules.channels.presentation.content_feed.http.response.resume_feed_import import (
    ResumeFeedImportResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.attach_feed_import import (
    attach_feed_import,
)
from src.modules.channels.presentation.content_feed.http.response.attach_feed_import import (
    AttachFeedImportResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.resolve_feed_import import (
    resolve_feed_import,
)
from src.modules.channels.presentation.content_feed.http.response.resolve_feed_import import (
    ResolveFeedImportResponse,
)
from src.modules.channels.presentation.content_feed.http.controller.get_feed_import import (
    get_feed_import,
)
from src.modules.channels.presentation.content_feed.http.response.get_feed_import import (
    GetFeedImportResponse,
)

router = APIRouter(
    prefix="/channels", tags=["content-feeds"], route_class=ContentFeedRoute
)


router.add_api_route(
    "/{channel_id}/content-feeds",
    create_content_feed,
    methods=["POST"],
    status_code=201,
    response_model=CreateContentFeedResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}",
    change_content_feed_source,
    methods=["PUT"],
    status_code=200,
    response_model=ChangeContentFeedSourceResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/enable",
    enable_content_feed,
    methods=["POST"],
    status_code=200,
    response_model=EnableContentFeedResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/disable",
    disable_content_feed,
    methods=["POST"],
    status_code=200,
    response_model=DisableContentFeedResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/access/rotate",
    rotate_feed_access,
    methods=["POST"],
    status_code=200,
    response_model=RotateFeedAccessResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/access/revoke",
    revoke_feed_access,
    methods=["POST"],
    status_code=200,
    response_model=RevokeFeedAccessResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}",
    get_content_feed,
    methods=["GET"],
    status_code=200,
    response_model=GetContentFeedResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)


router.add_api_route(
    "/{channel_id}/content-feeds",
    list_content_feeds,
    methods=["GET"],
    status_code=200,
    response_model=ListContentFeedsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/preview",
    preview_content_feed,
    methods=["POST"],
    status_code=200,
    response_model=PreviewContentFeedResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}",
    delete_content_feed,
    methods=["DELETE"],
    status_code=204,
    response_model=None,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


public_router = APIRouter(
    prefix="/api/channels/content-feeds",
    tags=["content-feeds"],
    route_class=ContentFeedRoute,
    dependencies=[Depends(prepare_channels_read)],
)
public_router.add_api_route(
    "/{feed_id}/feed.xml",
    get_content_feed_xml,
    methods=["GET"],
    response_model=None,
    responses={
        200: {
            "content": {
                "application/xml": {"schema": {"type": "string", "format": "binary"}}
            }
        }
    },
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/imports",
    request_feed_import,
    methods=["POST"],
    status_code=202,
    response_model=RequestFeedImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/imports/current/resume",
    resume_feed_import,
    methods=["POST"],
    status_code=200,
    response_model=ResumeFeedImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/imports/current/attach",
    attach_feed_import,
    methods=["POST"],
    status_code=200,
    response_model=AttachFeedImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/imports/current/resolve",
    resolve_feed_import,
    methods=["POST"],
    status_code=200,
    response_model=ResolveFeedImportResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


router.add_api_route(
    "/{channel_id}/content-feeds/{feed_id}/imports/current",
    get_feed_import,
    methods=["GET"],
    response_model=GetFeedImportResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
