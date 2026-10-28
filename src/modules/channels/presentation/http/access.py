from uuid import UUID

from fastapi import HTTPException

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.channel.error import (
    ChannelError,
    ChannelNotFoundError,
    ChannelRevisionConflictError,
    InvalidChannelNameError,
    InvalidResourceIdentityError,
)
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)


async def channel_access(
    context: RequestContext,
    authorization: AuthorizationServiceProtocol,
    action: str,
    channel_id: UUID | None = None,
) -> tuple[UUID, UUID]:
    """Проверяет tenant principal и существующий authorization port."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, detail={"code": "tenant_required"})
    tenant_id, actor_id = UUID(principal.tenant_id), UUID(principal.user_id)
    if not await authorization.can(
        user_id=actor_id,
        tenant_id=tenant_id,
        action="channels." + action,
        resource_type="channel",
        resource_id=channel_id,
    ):
        raise HTTPException(403, detail={"code": "access_denied"})
    return tenant_id, actor_id


def channel_http_error(
    error: (
        ChannelError | ChannelInputError | CipherNotConfigured | CiphertextUnreadable
    ),
) -> HTTPException:
    """Сохраняет публичные коды, не добавляя транспортные поля в Domain."""
    if isinstance(error, ChannelInputError):
        return HTTPException(422, detail={"code": error.code, "field": error.field})
    if isinstance(error, CipherNotConfigured):
        return HTTPException(
            503, detail={"code": "channels_not_configured", "field": None}
        )
    if isinstance(error, CiphertextUnreadable):
        return HTTPException(
            422, detail={"code": "credentials_unreadable", "field": None}
        )
    if isinstance(error, ChannelNotFoundError):
        return HTTPException(404, detail={"code": "channel_not_found", "field": None})
    if isinstance(error, ChannelRevisionConflictError):
        return HTTPException(409, detail={"code": "revision_conflict", "field": None})
    if isinstance(error, InvalidChannelNameError):
        return HTTPException(422, detail={"code": "name_invalid", "field": "name"})
    if isinstance(error, InvalidResourceIdentityError):
        return HTTPException(
            422, detail={"code": "resource_identity_unavailable", "field": None}
        )
    return HTTPException(422, detail={"code": "stored_channel_invalid", "field": None})
