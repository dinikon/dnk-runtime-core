from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.presentation.channel.depends import GetChannelHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.response.get_channel import (
    GetChannelResponse,
)


async def get_channel(
    channel_id: UUID, context: ChannelsReadContextDep, handler: GetChannelHandlerDep
) -> GetChannelResponse:
    """Преобразует HTTP get_channel в отдельный Command/Query и безопасный ответ."""
    try:
        request = GetChannelQuery(
            tenant_id=UUID(context.principal.tenant_id), channel_id=channel_id
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return GetChannelResponse(**asdict(result))
