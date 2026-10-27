from dataclasses import asdict
from typing import Literal

from fastapi import Query

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.query.list_channels.query import ListChannelsQuery
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import ListChannelsHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.http.response.list_channels import (
    ListChannelsResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_channels(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListChannelsHandlerDep,
    search: str = Query(default="", max_length=255),
    platform_kind: str | None = Query(default=None, max_length=64),
    status: Literal["pending", "verified", "error"] | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ListChannelsResponse:
    """Преобразует HTTP-параметры в конкретный запрос ListChannels."""
    tenant_id, _ = await channel_access(context, authorization, "read")
    try:
        result = await handler.execute(
            ListChannelsQuery(
                tenant_id=tenant_id,
                search=search,
                platform_kind=platform_kind,
                status=status,
                offset=offset,
                limit=limit,
            )
        )
    except (ChannelError, ChannelInputError) as error:
        raise channel_http_error(error) from None
    return ListChannelsResponse.model_validate(asdict(result))
