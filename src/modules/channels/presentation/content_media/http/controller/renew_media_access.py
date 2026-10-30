from uuid import UUID
from src.modules.channels.application.content_media.command.renew_media_access.command import (
    RenewMediaAccessCommand,
)
from src.modules.channels.presentation.content_media.depends import (
    RenewMediaAccessHandlerDep,
)
from src.modules.channels.presentation.content_media.http.request.renew_media_access import (
    RenewMediaAccessRequest,
)
from src.modules.channels.presentation.content_media.http.response.renew_media_access import (
    RenewMediaAccessResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def renew_media_access(
    channel_id: UUID,
    media_id: UUID,
    payload: RenewMediaAccessRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RenewMediaAccessHandlerDep,
) -> RenewMediaAccessResponse:
    """Проверяет channels.manage и выполняет конкретный сценарий renew_media_access."""
    await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        RenewMediaAccessCommand(channel_id, media_id, payload.expected_revision)
    )
    return RenewMediaAccessResponse.from_dto(result)
