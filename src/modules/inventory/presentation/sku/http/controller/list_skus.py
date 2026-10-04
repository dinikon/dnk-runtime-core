from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Query

from src.modules.inventory.application.sku.query.list_skus.query import ListSkusQuery
from src.modules.inventory.presentation.sku.depends import ListSkusHandlerDep
from src.modules.inventory.presentation.sku.http.response.list_skus import (
    ListSkuItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_skus(
    context: AuthenticatedRequestContextDep,
    handler: ListSkusHandlerDep,
    authorization: AuthorizationServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ListSkuItemResponse]:
    """Возвращает разрешённую страницу SKU текущего tenant."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="list",
        resource_type="inventory.sku",
    ):
        raise HTTPException(403, "SKU listing is not allowed.")
    result = await handler.execute(ListSkusQuery(limit=limit, offset=offset))
    return [ListSkuItemResponse.from_dto(item) for item in result.skus]
