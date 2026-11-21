from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.query import (
    ListItemPackagingsQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.presentation.inventory_item.depends import (
    ListItemPackagingsHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.request.list_item_packagings import (
    ListItemPackagingsRequest,
)
from src.modules.inventory.presentation.inventory_item.http.response.list_item_packagings import (
    ListItemPackagingsResponse,
)


async def list_item_packagings(
    inventory_item_id: UUID,
    params: Annotated[ListItemPackagingsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListItemPackagingsHandlerDep,
) -> ListItemPackagingsResponse:
    """Передаёт проверенные параметры страницы в read-сценарий существующего товара."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListItemPackagingsQuery(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                offset=params.offset,
                limit=params.limit,
                search=params.search,
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListItemPackagingsResponse.from_dto(result)
