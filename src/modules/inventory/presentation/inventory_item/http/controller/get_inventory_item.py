from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.query import (
    GetInventoryItemQuery,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    GetInventoryItemHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.response.get_inventory_item import (
    GetInventoryItemResponse,
)


async def get_inventory_item(
    inventory_item_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetInventoryItemHandlerDep,
) -> GetInventoryItemResponse:
    """Преобразует ID в запрос карточки и возвращает отдельный HTTP-контракт."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetInventoryItemQuery(InventoryItemIdVO(inventory_item_id))
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetInventoryItemResponse.from_dto(result)
