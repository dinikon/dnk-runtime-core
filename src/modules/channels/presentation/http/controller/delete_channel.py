from uuid import UUID

from fastapi import Query, Response

from src.modules.channels.application.command.delete_channel.command import (
    DeleteChannelCommand,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.error import ChannelError
from src.modules.channels.presentation.depends import DeleteChannelHandlerDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_channel(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: DeleteChannelHandlerDep,
    expected_revision: int = Query(ge=1),
) -> Response:
    """Преобразует HTTP-запрос в конкретную команду DeleteChannel."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    try:
        result = await handler.execute(
            DeleteChannelCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                channel_id=channel_id,
                expected_revision=expected_revision,
            )
        )
    except (ChannelError, ChannelInputError) as error:
        raise channel_http_error(error) from None
    return Response(status_code=204)
