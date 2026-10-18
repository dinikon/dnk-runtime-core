from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.channels.application.channel.query.list_channels.query import (
    ListChannelsQuery,
)
from src.modules.channels.presentation.channel.depends import ListChannelsHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.response.list_channels import (
    ListChannelsResponse,
)


async def list_channels(
    context: ChannelsReadContextDep,
    handler: ListChannelsHandlerDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ListChannelsResponse:
    """Преобразует HTTP list_channels в отдельный Command/Query и безопасный ответ."""
    try:
        request = ListChannelsQuery(
            tenant_id=UUID(context.principal.tenant_id), offset=offset, limit=limit
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return ListChannelsResponse(**asdict(result))
