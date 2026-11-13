from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_location.command.create_stock_location.command import (
    CreateStockLocationCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.stock_location.error import (
    StockLocationCodeAlreadyExistsError,
    StockLocationNotFoundError,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.presentation.stock_location.depends import (
    CreateStockLocationHandlerDep,
)
from src.modules.inventory.presentation.stock_location.http.request.create_stock_location import (
    CreateStockLocationRequest,
)
from src.modules.inventory.presentation.stock_location.http.response.create_stock_location import (
    CreateStockLocationResponse,
)


async def create_stock_location(
    warehouse_id: UUID,
    payload: CreateStockLocationRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateStockLocationHandlerDep,
) -> CreateStockLocationResponse:
    """Преобразует HTTP-ввод в команду без подмены активности и основной ссылки."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateStockLocationCommand(
                warehouse_id=WarehouseIdVO.from_value(warehouse_id),
                code=payload.code,
                name=payload.name,
                location_type=payload.location_type,
                parent_location_id=(
                    StockLocationIdVO.from_value(payload.parent_location_id)
                    if payload.parent_location_id is not None
                    else None
                ),
            )
        )
    except (WarehouseNotFoundError, StockLocationNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except StockLocationCodeAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateStockLocationResponse.from_dto(result)
