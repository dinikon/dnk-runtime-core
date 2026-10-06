from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.channel.http.context import (
    require_channel_context,
)
from src.modules.channels.presentation.channel.depends import GetChannelHandlerDep
from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.presentation.channel.http.response.get_channel import (
    GetChannelResponse,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError


async def get_channel(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetChannelHandlerDep,
) -> GetChannelResponse:
    """Выполняет get_channel, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        result = await handler.execute(
            GetChannelQuery(
                tenant_id=tenant_id,
                channel_id=channel_id,
            )
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return GetChannelResponse.from_dto(result)
