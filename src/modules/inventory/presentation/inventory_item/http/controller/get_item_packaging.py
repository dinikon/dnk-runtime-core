from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.query import (
    GetItemPackagingQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemComponentNotFoundError,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    GetItemPackagingHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.response.get_item_packaging import (
    GetItemPackagingResponse,
)


async def get_item_packaging(
    inventory_item_id: UUID,
    packaging_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetItemPackagingHandlerDep,
) -> GetItemPackagingResponse:
    """Читает упаковку внутри товара, не раскрывая чужую Entity по одному ID."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetItemPackagingQuery(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                packaging_id=ItemPackagingIdVO.from_value(packaging_id),
            )
        )
    except InventoryItemComponentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetItemPackagingResponse.from_dto(result)
