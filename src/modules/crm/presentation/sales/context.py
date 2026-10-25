from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.domain.auth.request_context import RequestContext


def sales_identity(context: RequestContext) -> tuple[UUID, UUID]:
    """Извлекает только доверенные tenant и actor текущего пользователя."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Требуется пространство tenant.")
    return UUID(principal.tenant_id), UUID(principal.user_id)
