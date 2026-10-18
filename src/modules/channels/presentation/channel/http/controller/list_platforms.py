from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.query.list_platforms.query import (
    ListPlatformsQuery,
)
from src.modules.channels.presentation.channel.depends import ListPlatformsHandlerDep
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.response.list_platforms import (
    ListPlatformsResponse,
)


async def list_platforms(
    context: ChannelsReadContextDep, handler: ListPlatformsHandlerDep
) -> ListPlatformsResponse:
    """Преобразует HTTP list_platforms в отдельный Command/Query и безопасный ответ."""
    try:
        request = ListPlatformsQuery(tenant_id=UUID(context.principal.tenant_id))
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return ListPlatformsResponse(**asdict(result))
