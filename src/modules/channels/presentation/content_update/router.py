from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.channels.presentation.content_update.http.controller.start_content_update import (
    start_content_update,
)
from src.modules.channels.presentation.content_update.http.response.start_content_update import (
    StartContentUpdateResponse,
)
from src.modules.channels.presentation.content_update.http.controller.confirm_content_update import (
    confirm_content_update,
)
from src.modules.channels.presentation.content_update.http.response.confirm_content_update import (
    ConfirmContentUpdateResponse,
)
from src.modules.channels.presentation.content_update.http.controller.retry_content_update import (
    retry_content_update,
)
from src.modules.channels.presentation.content_update.http.response.retry_content_update import (
    RetryContentUpdateResponse,
)
from src.modules.channels.presentation.content_update.http.controller.get_content_update import (
    get_content_update,
)
from src.modules.channels.presentation.content_update.http.response.get_content_update import (
    GetContentUpdateResponse,
)
from src.modules.channels.presentation.content_update.http.controller.list_content_updates import (
    list_content_updates,
)
from src.modules.channels.presentation.content_update.http.response.list_content_updates import (
    ListContentUpdatesResponse,
)

router = APIRouter(prefix="/channels", tags=["channels"], route_class=ChannelsRoute)
router.add_api_route(
    "/{channel_id}/content-updates",
    start_content_update,
    methods=["POST"],
    response_model=StartContentUpdateResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/content-updates/{run_id}/confirm",
    confirm_content_update,
    methods=["POST"],
    response_model=ConfirmContentUpdateResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/content-updates/{run_id}/retry",
    retry_content_update,
    methods=["POST"],
    response_model=RetryContentUpdateResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/content-updates/{run_id}",
    get_content_update,
    methods=["GET"],
    response_model=GetContentUpdateResponse,
)
router.add_api_route(
    "/{channel_id}/content-updates",
    list_content_updates,
    methods=["GET"],
    response_model=ListContentUpdatesResponse,
)
