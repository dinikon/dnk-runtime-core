from fastapi import APIRouter, Depends
from src.modules.channels.presentation.http_route import ChannelsRoute
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.depends.access import (
    require_channels_read_context,
    require_channels_manage_context,
)
from src.modules.channels.presentation.channel.http.controller.archive_channel import (
    archive_channel,
)
from src.modules.channels.presentation.channel.http.controller.create_channel import (
    create_channel,
)
from src.modules.channels.presentation.channel.http.response.create_channel import (
    CreateChannelResponse,
)
from src.modules.channels.presentation.channel.http.controller.create_connection import (
    create_connection,
)
from src.modules.channels.presentation.channel.http.response.create_connection import (
    CreateConnectionResponse,
)
from src.modules.channels.presentation.channel.http.controller.pause_connection import (
    pause_connection,
)
from src.modules.channels.presentation.channel.http.controller.resume_connection import (
    resume_connection,
)
from src.modules.channels.presentation.channel.http.controller.update_channel_policy import (
    update_channel_policy,
)
from src.modules.channels.presentation.channel.http.response.update_channel_policy import (
    UpdateChannelPolicyResponse,
)
from src.modules.channels.presentation.channel.http.controller.update_connection_settings import (
    update_connection_settings,
)
from src.modules.channels.presentation.channel.http.response.update_connection_settings import (
    UpdateConnectionSettingsResponse,
)
from src.modules.channels.presentation.channel.http.controller.verify_connection import (
    verify_connection,
)
from src.modules.channels.presentation.channel.http.response.verify_connection import (
    VerifyConnectionResponse,
)
from src.modules.channels.presentation.channel.http.controller.get_channel import (
    get_channel,
)
from src.modules.channels.presentation.channel.http.response.get_channel import (
    GetChannelResponse,
)
from src.modules.channels.presentation.channel.http.controller.get_connection import (
    get_connection,
)
from src.modules.channels.presentation.channel.http.response.get_connection import (
    GetConnectionResponse,
)
from src.modules.channels.presentation.channel.http.controller.get_platform_config import (
    get_platform_config,
)
from src.modules.channels.presentation.channel.http.response.get_platform_config import (
    GetPlatformConfigResponse,
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
    "",
    create_channel,
    methods=["POST"],
    status_code=201,
    response_model=CreateChannelResponse,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/platforms/{platform_kind}/config",
    get_platform_config,
    methods=["GET"],
    status_code=200,
    response_model=GetPlatformConfigResponse,
    dependencies=[Depends(require_channels_read_context)],
)
router.add_api_route(
    "",
    list_channels,
    methods=["GET"],
    status_code=200,
    response_model=ListChannelsResponse,
    dependencies=[Depends(require_channels_read_context)],
)
router.add_api_route(
    "/platforms",
    list_platforms,
    methods=["GET"],
    status_code=200,
    response_model=ListPlatformsResponse,
    dependencies=[Depends(require_channels_read_context)],
)
router.add_api_route(
    "/{channel_id}/archive",
    archive_channel,
    methods=["POST"],
    status_code=204,
    response_model=None,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}/connection",
    create_connection,
    methods=["POST"],
    status_code=201,
    response_model=CreateConnectionResponse,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}/connection/pause",
    pause_connection,
    methods=["POST"],
    status_code=204,
    response_model=None,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}/connection/resume",
    resume_connection,
    methods=["POST"],
    status_code=204,
    response_model=None,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}",
    update_channel_policy,
    methods=["PATCH"],
    status_code=200,
    response_model=UpdateChannelPolicyResponse,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}/connection",
    update_connection_settings,
    methods=["PATCH"],
    status_code=200,
    response_model=UpdateConnectionSettingsResponse,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}/connection/verify",
    verify_connection,
    methods=["POST"],
    status_code=202,
    response_model=VerifyConnectionResponse,
    dependencies=[Depends(require_channels_manage_context), Depends(require_csrf)],
)
router.add_api_route(
    "/{channel_id}",
    get_channel,
    methods=["GET"],
    status_code=200,
    response_model=GetChannelResponse,
    dependencies=[Depends(require_channels_read_context)],
)
router.add_api_route(
    "/{channel_id}/connection",
    get_connection,
    methods=["GET"],
    status_code=200,
    response_model=GetConnectionResponse,
    dependencies=[Depends(require_channels_read_context)],
)
