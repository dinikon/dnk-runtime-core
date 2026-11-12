from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.inventory_item.command.create_inventory_item.command import (
    CreateInventoryItemCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemBarcodeAlreadyExistsError,
    InventoryItemSkuAlreadyExistsError,
)
from src.modules.inventory.presentation.inventory_item.depends import (
    CreateInventoryItemHandlerDep,
)
from src.modules.inventory.presentation.inventory_item.http.request.create_inventory_item import (
    CreateInventoryItemRequest,
)
from src.modules.inventory.presentation.inventory_item.http.response.create_inventory_item import (
    CreateInventoryItemResponse,
)


async def create_inventory_item(
    payload: CreateInventoryItemRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateInventoryItemHandlerDep,
) -> CreateInventoryItemResponse:
    """Преобразует POST в команду и переводит ожидаемые отказы в HTTP-статусы."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateInventoryItemCommand(
                sku=payload.sku,
                base_uom=payload.base_uom,
                quantity_step=(
                    payload.quantity_rules.step
                    if payload.quantity_rules is not None
                    else None
                ),
                tracking_mode=payload.tracking_mode,
                expiration_mode=payload.expiration_mode,
                barcodes=tuple(payload.barcodes),
            )
        )
    except (
        InventoryItemSkuAlreadyExistsError,
        InventoryItemBarcodeAlreadyExistsError,
    ) as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateInventoryItemResponse.from_dto(result)
