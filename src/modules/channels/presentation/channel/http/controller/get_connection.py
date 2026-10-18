from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.query.get_connection.query import (
    GetConnectionQuery,
)
from src.modules.channels.presentation.channel.depends import GetConnectionHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.response.get_connection import (
    GetConnectionResponse,
)


async def get_connection(
    channel_id: UUID, context: ChannelsReadContextDep, handler: GetConnectionHandlerDep
) -> GetConnectionResponse:
    """Преобразует HTTP get_connection в отдельный Command/Query и безопасный ответ."""
    try:
        request = GetConnectionQuery(
            tenant_id=UUID(context.principal.tenant_id), channel_id=channel_id
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return GetConnectionResponse(**asdict(result))
