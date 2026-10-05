from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.domain.auth.request_context import RequestContext


def require_category_context(context: RequestContext) -> tuple[UUID, UUID]:
    """Возвращает доверенные tenant и actor текущего запроса."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    return UUID(principal.tenant_id), UUID(principal.user_id)
