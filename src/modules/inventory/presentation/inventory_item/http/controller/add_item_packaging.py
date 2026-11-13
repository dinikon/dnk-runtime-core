from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.add_item_packaging.command import (
    AddItemPackagingCommand,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.presentation.inventory_item.depends import (
    AddItemPackagingHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.request.add_item_packaging import (
    AddItemPackagingRequest,
)
from src.modules.inventory.presentation.inventory_item.http.response.add_item_packaging import (
    AddItemPackagingResponse,
)


async def add_item_packaging(
    inventory_item_id: UUID,
    payload: AddItemPackagingRequest,
    context: AuthenticatedRequestContextDep,
    handler: AddItemPackagingHandlerDep,
) -> AddItemPackagingResponse:
    """Создаёт команду назначения тары и явно переводит ожидаемые ошибки в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            AddItemPackagingCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                packaging_type_id=PackagingTypeIdVO.from_value(
                    payload.packaging_type_id
                ),
                code=payload.code,
                name=payload.name,
                content_quantity=payload.content_quantity,
                content_uom=payload.content_uom,
            )
        )
    except (InventoryItemNotFoundError, PackagingTypeNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InventoryItemConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return AddItemPackagingResponse.from_dto(result)
