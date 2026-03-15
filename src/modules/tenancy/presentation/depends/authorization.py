from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from src.modules.shared.depends.authorization import (
    AuthorizationServiceDep,
    get_authorization_service,
)
from src.modules.tenancy.domain.permissions import TenancyAction


async def authorize_admin_create_tenant(
    authorization_service: AuthorizationServiceDep,
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-Id")] = None,
) -> None:
    allowed = await authorization_service.can(
        user_id=actor_id,
        tenant_id=None,
        action=TenancyAction.ADMIN_CREATE_TENANT,
        resource_type="tenant",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions.",
        )


AdminCreateTenantAuthorizationDep = Annotated[
    None,
    Depends(authorize_admin_create_tenant),
]

__all__ = [
    "get_authorization_service",
    "AuthorizationServiceDep",
    "authorize_admin_create_tenant",
    "AdminCreateTenantAuthorizationDep",
]
