from uuid import UUID
from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.command import (
    UpdateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.error import (
    InvalidInventoryItemUpdateError,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemSkuAlreadyExistsError,
    InventoryItemBarcodeAlreadyExistsError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    UpdateInventoryItemHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.request.patch_inventory_item import (
    PatchInventoryItemRequest,
)
from src.modules.inventory.presentation.inventory_item.http.response.patch_inventory_item import (
    PatchInventoryItemResponse,
)


async def patch_inventory_item(
    inventory_item_id: UUID,
    payload: PatchInventoryItemRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateInventoryItemHandlerDep,
) -> PatchInventoryItemResponse:
    """Передаёт в команду только явно присутствующие поля PATCH."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateInventoryItemCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                fields=frozenset(payload.model_fields_set),
                sku=payload.sku,
                base_uom=payload.base_uom,
                quantity_step=(
                    payload.quantity_rules.step
                    if payload.quantity_rules is not None
                    else None
                ),
                tracking_mode=payload.tracking_mode,
                expiration_mode=payload.expiration_mode,
                barcodes=(
                    tuple(payload.barcodes) if payload.barcodes is not None else None
                ),
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (
        InventoryItemSkuAlreadyExistsError,
        InventoryItemBarcodeAlreadyExistsError,
    ) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (InventoryError, InvalidInventoryItemUpdateError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchInventoryItemResponse.from_dto(result)
