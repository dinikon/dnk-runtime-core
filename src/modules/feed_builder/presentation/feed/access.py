from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def require_feed_access(
    context: RequestContext,
    authorization: AuthorizationServiceProtocol,
    *,
    action: str,
    feed_id: UUID | None = None,
) -> None:
    """Проверяет доверенный tenant-контекст и существующий контракт авторизации Identity."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Требуется tenant-контекст.")
    allowed = await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action=action,
        resource_type="feed_builder.feed",
        resource_id=feed_id,
    )
    if not allowed:
        raise HTTPException(403, "Недостаточно прав для операции с Feed.")


async def require_feed_access_management(
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> None:
    """Проверяет право читать и управлять доступом к выбранному фиду."""
    for action in ("feed_builder.feed.read", "feed_builder.feed.update"):
        await require_feed_access(
            context, authorization, action=action, feed_id=feed_id
        )
