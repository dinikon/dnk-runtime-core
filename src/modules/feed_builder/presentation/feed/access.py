from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
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
