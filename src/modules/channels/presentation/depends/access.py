from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.domain.auth.request_context import RequestContext


async def require_channels_read_context(
    context: AuthenticatedRequestContextDep, authorization: AuthorizationServiceDep
) -> RequestContext:
    """Проверяет доверенный tenant и право чтения Channels."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "tenant_context_required")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="channels.read",
        resource_type="channel",
    ):
        raise HTTPException(403, "channels_access_denied")
    return context


async def require_channels_manage_context(
    context: AuthenticatedRequestContextDep, authorization: AuthorizationServiceDep
) -> RequestContext:
    """Проверяет право управления источниками и запуска чтения."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "tenant_context_required")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="channels.manage",
        resource_type="channel",
    ):
        raise HTTPException(403, "channels_access_denied")
    return context


ChannelsReadContextDep = Annotated[
    RequestContext, Depends(require_channels_read_context)
]
ChannelsManageContextDep = Annotated[
    RequestContext, Depends(require_channels_manage_context)
]
