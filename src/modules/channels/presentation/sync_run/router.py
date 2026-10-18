from fastapi import APIRouter, Depends
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.depends.access import (
    require_channels_read_context,
    require_channels_manage_context,
)
from src.modules.channels.presentation.sync_run.http.controller.start_publication_initialization import (
    start_publication_initialization,
)
from src.modules.channels.presentation.sync_run.http.response.start_publication_initialization import (
    StartPublicationInitializationResponse,
)
from src.modules.channels.presentation.sync_run.http.controller.get_publication_initialization import (
    get_publication_initialization,
)
from src.modules.channels.presentation.sync_run.http.response.get_publication_initialization import (
    GetPublicationInitializationResponse,
)

router = APIRouter(prefix="/channels", tags=["channels"], route_class=ChannelsRoute)
router.add_api_route(
    "/connections/{connection_id}/initialization",
    start_publication_initialization,
    methods=["POST"],
    status_code=202,
    response_model=StartPublicationInitializationResponse,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/connections/{connection_id}/initialization",
    get_publication_initialization,
    methods=["GET"],
    status_code=200,
    response_model=GetPublicationInitializationResponse,
    dependencies=[Depends(require_channels_read_context)],
)
