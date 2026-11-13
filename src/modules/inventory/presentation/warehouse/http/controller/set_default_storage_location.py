from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.warehouse.command.set_default_storage_location.command import (
    SetDefaultStorageLocationCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.presentation.warehouse.depends import (
    SetDefaultStorageLocationHandlerDep,
)
from src.modules.inventory.presentation.warehouse.http.request.set_default_storage_location import (
    SetDefaultStorageLocationRequest,
)
from src.modules.inventory.presentation.warehouse.http.response.set_default_storage_location import (
    SetDefaultStorageLocationResponse,
)


async def set_default_storage_location(
    warehouse_id: UUID,
    payload: SetDefaultStorageLocationRequest,
    context: AuthenticatedRequestContextDep,
    handler: SetDefaultStorageLocationHandlerDep,
) -> SetDefaultStorageLocationResponse:
    """Передаёт выбор в Application и переводит отсутствие ссылок и Domain-отказы в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetDefaultStorageLocationCommand(
                warehouse_id=WarehouseIdVO(warehouse_id),
                location_id=StockLocationIdVO(payload.location_id),
            )
        )
    except (WarehouseNotFoundError, StockLocationNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return SetDefaultStorageLocationResponse.from_dto(result)
