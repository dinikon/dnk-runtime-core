from dataclasses import asdict
from uuid import UUID
from src.modules.channels.application.channel.query.get_platform_config.query import (
    GetPlatformConfigQuery,
)
from src.modules.channels.presentation.channel.depends import (
    GetPlatformConfigHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.channel.http.response.get_platform_config import (
    GetPlatformConfigResponse,
)


async def get_platform_config(
    platform_kind: str,
    context: ChannelsReadContextDep,
    handler: GetPlatformConfigHandlerDep,
) -> GetPlatformConfigResponse:
    """Преобразует HTTP get_platform_config в отдельный Command/Query и безопасный ответ."""
    try:
        request = GetPlatformConfigQuery(
            tenant_id=UUID(context.principal.tenant_id), platform_kind=platform_kind
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return GetPlatformConfigResponse(**asdict(result))
