from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.channel.http.context import (
    require_channel_context,
)
from src.modules.channels.presentation.channel.depends import ListChannelsHandlerDep
from src.modules.channels.application.channel.query.list_channels.query import (
    ListChannelsQuery,
)
from src.modules.channels.presentation.channel.http.response.list_channels import (
    ListChannelItemResponse,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError


async def list_channels(
    context: AuthenticatedRequestContextDep,
    handler: ListChannelsHandlerDep,
) -> list[ListChannelItemResponse]:
    """Выполняет list_channels, явно преобразуя вход, результат и ожидаемые ошибки."""
    tenant_id, actor_id = require_channel_context(context)
    try:
        result = await handler.execute(
            ListChannelsQuery(
                tenant_id=tenant_id,
            )
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return [ListChannelItemResponse.from_dto(item) for item in result]
