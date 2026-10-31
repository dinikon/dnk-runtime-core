from dataclasses import asdict

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.query.list_platforms.query import (
    ListPlatformsQuery,
)
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import ListPlatformsHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.http.response.list_platforms import (
    ListPlatformsResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_platforms(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListPlatformsHandlerDep,
) -> ListPlatformsResponse:
    """Преобразует HTTP-параметры в конкретный запрос ListPlatforms."""
    tenant_id, _ = await channel_access(context, authorization, "read")
    try:
        result = await handler.execute(ListPlatformsQuery(tenant_id=tenant_id))
    except (ChannelError, ChannelInputError) as error:
        raise channel_http_error(error) from None
    return ListPlatformsResponse.model_validate(asdict(result))
