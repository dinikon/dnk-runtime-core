from uuid import UUID
from fastapi import HTTPException, Response

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.command import (
    DeleteInventoryItemCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemInUseError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    DeleteInventoryItemHandlerDep,
)


async def delete_inventory_item(
    inventory_item_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteInventoryItemHandlerDep,
) -> Response:
    """Удаляет существующую позицию по ID и возвращает пустой 204."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteInventoryItemCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InventoryItemInUseError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(status_code=204)
