"""HTTP-маршруты агрегата Channels."""

from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http.safe_route import ChannelsRoute
from src.modules.channels.presentation.sync_run.http.controller.start_sync_run import (
    start_sync_run,
)
from src.modules.channels.presentation.sync_run.http.response.start_sync_run import (
    StartSyncRunResponse,
)
from src.modules.channels.presentation.sync_run.http.controller.get_latest_sync_run import (
    get_latest_sync_run,
)
from src.modules.channels.presentation.sync_run.http.response.get_latest_sync_run import (
    GetLatestSyncRunResponse,
)
from src.modules.channels.presentation.sync_run.http.controller.get_sync_run import (
    get_sync_run,
)
from src.modules.channels.presentation.sync_run.http.response.get_sync_run import (
    GetSyncRunResponse,
)

router = APIRouter(
    prefix="/channels/{channel_id}", tags=["channels"], route_class=ChannelsRoute
)
router.add_api_route(
    "/sync-runs",
    start_sync_run,
    methods=["POST"],
    status_code=202,
    response_model=StartSyncRunResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/sync-runs/latest",
    get_latest_sync_run,
    methods=["GET"],
    status_code=200,
    response_model=GetLatestSyncRunResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/sync-runs/{run_id}",
    get_sync_run,
    methods=["GET"],
    status_code=200,
    response_model=GetSyncRunResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
