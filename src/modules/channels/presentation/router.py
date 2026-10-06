from fastapi import APIRouter, Depends
from src.modules.channels.presentation.http.route import ChannelRoute
from src.modules.channels.presentation.http.response.channel import (
    ChannelResponse,
    ChannelKindResponse,
    ChannelConfigResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.http.controller.create_channel import (
    create_channel,
)
from src.modules.channels.presentation.http.controller.update_channel import (
    update_channel,
)
from src.modules.channels.presentation.http.controller.delete_channel import (
    delete_channel,
)
from src.modules.channels.presentation.http.controller.get_channel import get_channel
from src.modules.channels.presentation.http.controller.list_channels import (
    list_channels,
)
from src.modules.channels.presentation.http.controller.list_kinds import list_kinds
from src.modules.channels.presentation.http.controller.get_kind_config import (
    get_kind_config,
)

router = APIRouter(
    prefix="/channels",
    tags=["channels"],
    route_class=ChannelRoute,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/kinds",
    list_kinds,
    methods=["GET"],
    response_model=list[ChannelKindResponse],
    status_code=200,
    dependencies=[],
)
router.add_api_route(
    "/kinds/{kind}/config",
    get_kind_config,
    methods=["GET"],
    response_model=ChannelConfigResponse,
    status_code=200,
    dependencies=[],
)
router.add_api_route(
    "",
    create_channel,
    methods=["POST"],
    response_model=ChannelResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "",
    list_channels,
    methods=["GET"],
    response_model=list[ChannelResponse],
    status_code=200,
    dependencies=[],
)
router.add_api_route(
    "/{channel_id}",
    get_channel,
    methods=["GET"],
    response_model=ChannelResponse,
    status_code=200,
    dependencies=[],
)
router.add_api_route(
    "/{channel_id}",
    update_channel,
    methods=["PATCH"],
    response_model=ChannelResponse,
    status_code=200,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}",
    delete_channel,
    methods=["DELETE"],
    response_model=None,
    status_code=204,
    dependencies=[Depends(require_csrf)],
)
