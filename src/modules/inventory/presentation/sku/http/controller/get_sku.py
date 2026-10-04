from uuid import UUID

from fastapi import HTTPException

from src.modules.inventory.application.sku.query.get_sku.query import GetSkuQuery
from src.modules.inventory.domain.sku.error import SkuNotFoundError
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO
from src.modules.inventory.presentation.sku.depends import GetSkuHandlerDep
from src.modules.inventory.presentation.sku.http.response.get_sku import GetSkuResponse
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_sku(
    sku_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetSkuHandlerDep,
    authorization: AuthorizationServiceDep,
) -> GetSkuResponse:
    """Читает SKU только после проверки доверенного tenant и разрешения."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if not await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="read",
        resource_type="inventory.sku",
        resource_id=sku_id,
    ):
        raise HTTPException(403, "SKU reading is not allowed.")
    try:
        result = await handler.execute(GetSkuQuery(SkuIdVO.from_value(sku_id)))
    except SkuNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetSkuResponse.from_dto(result)
