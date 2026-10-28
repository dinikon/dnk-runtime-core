from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http.safe_route import ChannelsRoute
from src.modules.channels.presentation.channel.http.controller.create_channel import (
    create_channel,
)
from src.modules.channels.presentation.channel.http.response.create_channel import (
    CreateChannelResponse,
)
from src.modules.channels.presentation.channel.http.controller.update_channel import (
    update_channel,
)
from src.modules.channels.presentation.channel.http.response.update_channel import (
    UpdateChannelResponse,
)
from src.modules.channels.presentation.channel.http.controller.verify_connection import (
    verify_connection,
)
from src.modules.channels.presentation.channel.http.response.verify_connection import (
    VerifyConnectionResponse,
)
from src.modules.channels.presentation.channel.http.controller.delete_channel import (
    delete_channel,
)
from src.modules.channels.presentation.channel.http.controller.get_channel import (
    get_channel,
)
from src.modules.channels.presentation.channel.http.response.get_channel import (
    GetChannelResponse,
)
from src.modules.channels.presentation.channel.http.controller.list_channels import (
    list_channels,
)
from src.modules.channels.presentation.channel.http.response.list_channels import (
    ListChannelsResponse,
)
from src.modules.channels.presentation.channel.http.controller.list_platforms import (
    list_platforms,
)
from src.modules.channels.presentation.channel.http.response.list_platforms import (
    ListPlatformsResponse,
)

router = APIRouter(prefix="/channels", tags=["channels"], route_class=ChannelsRoute)
router.add_api_route(
    "/platforms",
    list_platforms,
    methods=["GET"],
    status_code=200,
    response_model=ListPlatformsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_channels,
    methods=["GET"],
    status_code=200,
    response_model=ListChannelsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_channel,
    methods=["POST"],
    status_code=201,
    response_model=CreateChannelResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{channel_id}",
    get_channel,
    methods=["GET"],
    status_code=200,
    response_model=GetChannelResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{channel_id}",
    update_channel,
    methods=["PATCH"],
    status_code=200,
    response_model=UpdateChannelResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{channel_id}/connection/verify",
    verify_connection,
    methods=["POST"],
    status_code=202,
    response_model=VerifyConnectionResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{channel_id}",
    delete_channel,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
