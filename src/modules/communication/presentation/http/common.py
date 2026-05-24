from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from src.modules.shared.domain.identity_context import RequestContext


def require_tenant_id(context: RequestContext) -> UUID:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return principal.tenant_id


__all__ = ["require_tenant_id"]
