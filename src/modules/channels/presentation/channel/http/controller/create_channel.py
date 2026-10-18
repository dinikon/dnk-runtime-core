from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.presentation.channel.depends import CreateChannelHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsManageContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.request.create_channel import (
    CreateChannelRequest,
)
from src.modules.channels.presentation.channel.http.response.create_channel import (
    CreateChannelResponse,
)


async def create_channel(
    payload: CreateChannelRequest,
    context: ChannelsManageContextDep,
    handler: CreateChannelHandlerDep,
) -> CreateChannelResponse:
    """Преобразует HTTP create_channel в отдельный Command/Query и безопасный ответ."""
    try:
        request = CreateChannelCommand(
            tenant_id=UUID(context.principal.tenant_id),
            actor_id=UUID(context.principal.user_id),
            name=payload.name,
            platform_kind=payload.platform_kind,
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return CreateChannelResponse(**asdict(result))
