from fastapi import APIRouter, Depends, Response

from src.modules.feed_builder.presentation.access_key.http.controller.issue_feed_access_key import (
    issue_feed_access_key,
)
from src.modules.feed_builder.presentation.access_key.http.controller.list_feed_access_keys import (
    list_feed_access_keys,
)
from src.modules.feed_builder.presentation.access_key.http.controller.revoke_feed_access_key import (
    revoke_feed_access_key,
)
from src.modules.feed_builder.presentation.access_key.http.response.issue_feed_access_key import (
    IssueFeedAccessKeyResponse,
)
from src.modules.feed_builder.presentation.access_key.http.response.list_feed_access_keys import (
    ListFeedAccessKeysResponse,
)
from src.modules.feed_builder.presentation.feed.access import (
    require_feed_access_management,
)
from src.modules.feed_builder.presentation.feed.http.schema.body_limit import (
    SchemaBodyLimitRoute,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(
    prefix="/feed-builder/feeds/{feed_id}/access-tokens",
    tags=["feed-builder-access"],
    route_class=SchemaBodyLimitRoute,
    dependencies=[Depends(require_feed_access_management)],
)
router.add_api_route(
    "",
    list_feed_access_keys,
    methods=["GET"],
    response_model=ListFeedAccessKeysResponse,
)
router.add_api_route(
    "",
    issue_feed_access_key,
    methods=["POST"],
    status_code=201,
    response_model=IssueFeedAccessKeyResponse,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{token_id}",
    revoke_feed_access_key,
    methods=["DELETE"],
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_csrf)],
)
