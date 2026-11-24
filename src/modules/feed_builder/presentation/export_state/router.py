from fastapi import APIRouter, Depends

from src.modules.feed_builder.presentation.export_state.http.controller.download_public_feed import (
    download_public_feed,
    download_public_feed_xml,
)
from src.modules.feed_builder.presentation.export_state.http.controller.get_feed_export_state import (
    get_feed_export_state,
)
from src.modules.feed_builder.presentation.export_state.http.controller.list_latest_feed_export_issues import (
    list_latest_feed_export_issues,
)
from src.modules.feed_builder.presentation.export_state.http.controller.request_feed_refresh import (
    request_feed_refresh,
)
from src.modules.feed_builder.presentation.export_state.http.controller.rotate_feed_public_link import (
    rotate_feed_public_link,
)
from src.modules.feed_builder.presentation.export_state.http.response.get_feed_export_state import (
    GetFeedExportStateResponse,
)
from src.modules.feed_builder.presentation.export_state.http.response.list_latest_feed_export_issues import (
    ListLatestFeedExportIssuesResponse,
)
from src.modules.feed_builder.presentation.export_state.http.response.request_feed_refresh import (
    RequestFeedRefreshResponse,
)
from src.modules.feed_builder.presentation.export_state.http.response.rotate_feed_public_link import (
    RotateFeedPublicLinkResponse,
)
from src.modules.feed_builder.presentation.export_state.http.urls import (
    PUBLIC_FEED_PREFIX,
)
from src.modules.feed_builder.presentation.feed.export_depends import (
    prepare_export_transaction,
)
from src.modules.feed_builder.presentation.feed.http.schema.body_limit import (
    SchemaBodyLimitRoute,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(
    prefix="/feed-builder/feeds",
    tags=["feed-builder-export"],
    route_class=SchemaBodyLimitRoute,
)
router.add_api_route(
    "/{feed_id}/export",
    get_feed_export_state,
    methods=["GET"],
    response_model=GetFeedExportStateResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{feed_id}/export/issues",
    list_latest_feed_export_issues,
    methods=["GET"],
    response_model=ListLatestFeedExportIssuesResponse,
    dependencies=[
        Depends(prepare_export_transaction),
        Depends(require_authenticated_request_context),
    ],
)
router.add_api_route(
    "/{feed_id}/export/refresh",
    request_feed_refresh,
    methods=["POST"],
    status_code=202,
    response_model=RequestFeedRefreshResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{feed_id}/public-link/rotate",
    rotate_feed_public_link,
    methods=["POST"],
    response_model=RotateFeedPublicLinkResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)

public_router = APIRouter(prefix=PUBLIC_FEED_PREFIX, tags=["public-feed"])
public_router.add_api_route(
    "/{public_link_id}/feed.csv", download_public_feed, methods=["GET"]
)
public_router.add_api_route(
    "/{public_link_id}/feed.xml", download_public_feed_xml, methods=["GET"]
)
