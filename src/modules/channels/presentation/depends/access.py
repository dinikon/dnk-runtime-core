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


async def require_catalog_link_context(
    context: ChannelsManageContextDep, authorization: AuthorizationServiceDep
) -> RequestContext:
    """Проверяет Channels manage и право чтения выбираемого Catalog."""
    if not await authorization.can(
        user_id=UUID(context.principal.user_id),
        tenant_id=UUID(context.principal.tenant_id),
        action="catalog.read",
        resource_type="catalog_item",
    ):
        raise HTTPException(403, "catalog_access_denied")
    return context


CatalogLinkContextDep = Annotated[RequestContext, Depends(require_catalog_link_context)]


async def require_catalog_create_context(
    context: CatalogLinkContextDep, authorization: AuthorizationServiceDep
) -> RequestContext:
    """Не позволяет обойти право создания товара через импорт публикации."""
    if not await authorization.can(
        user_id=UUID(context.principal.user_id),
        tenant_id=UUID(context.principal.tenant_id),
        action="catalog.create",
        resource_type="catalog_item",
    ):
        raise HTTPException(403, "catalog_access_denied")
    return context


CatalogCreateContextDep = Annotated[
    RequestContext, Depends(require_catalog_create_context)
]
