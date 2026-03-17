from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from src.modules.shared.depends import (
    AuthenticatedRequestContextDep,
    require_authenticated_request_context,
)
from src.modules.shared.kernel.request_context import RequestContext


def get_authenticated_tenant_id(
    context: AuthenticatedRequestContextDep,
) -> UUID:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        return UUID(principal.tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        ) from exc


CrmAuthenticatedRequestContextDep = Annotated[
    RequestContext,
    Depends(require_authenticated_request_context),
]
CrmTenantIdDep = Annotated[UUID, Depends(get_authenticated_tenant_id)]

__all__ = [
    "CrmAuthenticatedRequestContextDep",
    "CrmTenantIdDep",
    "get_authenticated_tenant_id",
]
