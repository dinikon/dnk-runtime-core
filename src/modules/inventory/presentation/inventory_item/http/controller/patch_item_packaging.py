from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.update_item_packaging.command import (
    UpdateItemPackagingCommand,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.presentation.inventory_item.depends import (
    UpdateItemPackagingHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.request.patch_item_packaging import (
    PatchItemPackagingRequest,
)
from src.modules.inventory.presentation.inventory_item.http.response.patch_item_packaging import (
    PatchItemPackagingResponse,
)


async def patch_item_packaging(
    inventory_item_id: UUID,
    packaging_id: UUID,
    payload: PatchItemPackagingRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateItemPackagingHandlerDep,
) -> PatchItemPackagingResponse:
    """Преобразует PATCH в команду и явно переводит ожидаемые ошибки в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateItemPackagingCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                packaging_id=ItemPackagingIdVO.from_value(packaging_id),
                fields=frozenset(payload.model_fields_set),
                packaging_type_id=(
                    PackagingTypeIdVO.from_value(payload.packaging_type_id)
                    if payload.packaging_type_id is not None
                    else None
                ),
                code=payload.code,
                name=payload.name,
                content_quantity=payload.content_quantity,
                content_uom=payload.content_uom,
            )
        )
    except (
        InventoryItemNotFoundError,
        InventoryItemComponentNotFoundError,
        PackagingTypeNotFoundError,
    ) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InventoryItemConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchItemPackagingResponse.from_dto(result)
