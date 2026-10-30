from uuid import UUID
from src.modules.channels.application.content_media.command.revoke_media_access.command import (
    RevokeMediaAccessCommand,
)
from src.modules.channels.presentation.content_media.depends import (
    RevokeMediaAccessHandlerDep,
)
from src.modules.channels.presentation.content_media.http.request.revoke_media_access import (
    RevokeMediaAccessRequest,
)
from src.modules.channels.presentation.content_media.http.response.revoke_media_access import (
    RevokeMediaAccessResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def revoke_media_access(
    channel_id: UUID,
    media_id: UUID,
    payload: RevokeMediaAccessRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RevokeMediaAccessHandlerDep,
) -> RevokeMediaAccessResponse:
    """Проверяет channels.manage и выполняет конкретный сценарий revoke_media_access."""
    await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        RevokeMediaAccessCommand(channel_id, media_id, payload.expected_revision)
    )
    return RevokeMediaAccessResponse.from_dto(result)
