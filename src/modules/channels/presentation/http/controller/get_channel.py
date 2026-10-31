from dataclasses import asdict
from uuid import UUID

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import GetChannelHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.http.response.get_channel import (
    GetChannelResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_channel(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetChannelHandlerDep,
) -> GetChannelResponse:
    """Преобразует HTTP-параметры в конкретный запрос GetChannel."""
    tenant_id, _ = await channel_access(context, authorization, "read", channel_id)
    try:
        result = await handler.execute(
            GetChannelQuery(tenant_id=tenant_id, channel_id=channel_id)
        )
    except (ChannelError, ChannelInputError) as error:
        raise channel_http_error(error) from None
    return GetChannelResponse.model_validate(asdict(result.channel))
