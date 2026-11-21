from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_location.command.update_stock_location.command import (
    UpdateStockLocationCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_location.error import (
    StockLocationNotFoundError,
    StockLocationCodeAlreadyExistsError,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.error import (
    WarehouseNotFoundError,
    DefaultStorageLocationInUseError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.presentation.stock_location.depends import (
    UpdateStockLocationHandlerDep,
)
from src.modules.inventory.presentation.stock_location.http.request.patch_stock_location import (
    PatchStockLocationRequest,
)
from src.modules.inventory.presentation.stock_location.http.response.patch_stock_location import (
    PatchStockLocationResponse,
)


async def patch_stock_location(
    warehouse_id: UUID,
    location_id: UUID,
    payload: PatchStockLocationRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateStockLocationHandlerDep,
) -> PatchStockLocationResponse:
    """Преобразует PATCH в команду и переводит предметные отказы в HTTP-статусы."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateStockLocationCommand(
                warehouse_id=WarehouseIdVO.from_value(warehouse_id),
                location_id=StockLocationIdVO.from_value(location_id),
                fields=frozenset(payload.model_fields_set),
                code=payload.code,
                name=payload.name,
                is_active=payload.is_active,
            )
        )
    except (WarehouseNotFoundError, StockLocationNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (
        StockLocationCodeAlreadyExistsError,
        DefaultStorageLocationInUseError,
    ) as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchStockLocationResponse.from_dto(result)
