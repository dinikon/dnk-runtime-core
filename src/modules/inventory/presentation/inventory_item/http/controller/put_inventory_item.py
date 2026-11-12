from uuid import UUID
from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.command import (
    UpdateInventoryItemCommand,
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
from src.modules.inventory.presentation.inventory_item.http.request.put_inventory_item import (
    PutInventoryItemRequest,
)
from src.modules.inventory.presentation.inventory_item.http.response.put_inventory_item import (
    PutInventoryItemResponse,
)


async def put_inventory_item(
    inventory_item_id: UUID,
    payload: PutInventoryItemRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateInventoryItemHandlerDep,
) -> PutInventoryItemResponse:
    """Полностью заменяет редактируемые данные существующей позиции без upsert."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateInventoryItemCommand(
                inventory_item_id=InventoryItemIdVO.from_value(inventory_item_id),
                fields=frozenset(
                    {
                        "sku",
                        "base_uom",
                        "quantity_rules",
                        "tracking_mode",
                        "expiration_mode",
                        "barcodes",
                    }
                ),
                sku=payload.sku,
                base_uom=payload.base_uom,
                quantity_step=payload.quantity_rules.step,
                tracking_mode=payload.tracking_mode,
                expiration_mode=payload.expiration_mode,
                barcodes=tuple(payload.barcodes),
            )
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (
        InventoryItemSkuAlreadyExistsError,
        InventoryItemBarcodeAlreadyExistsError,
    ) as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutInventoryItemResponse.from_dto(result)
