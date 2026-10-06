from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


def require_channel_context(
    context: AuthenticatedRequestContextDep,
) -> tuple[UUID, UUID]:
    """Извлекает tenant и инициатора исключительно из аутентифицированного контекста."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    return UUID(principal.tenant_id), UUID(principal.user_id)
