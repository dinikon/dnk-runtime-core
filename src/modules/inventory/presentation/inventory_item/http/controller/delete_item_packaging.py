from uuid import UUID

from fastapi import HTTPException, Response

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.delete_item_packaging.command import (
    DeleteItemPackagingCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemComponentNotFoundError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    DeleteItemPackagingHandlerDep,
)


async def delete_item_packaging(
    inventory_item_id: UUID,
    packaging_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteItemPackagingHandlerDep,
) -> Response:
    """Удаляет собственную упаковку товара и возвращает пустой ответ 204."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteItemPackagingCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                packaging_id=ItemPackagingIdVO.from_value(packaging_id),
            )
        )
    except (InventoryItemNotFoundError, InventoryItemComponentNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(status_code=204)
