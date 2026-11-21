from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.query import (
    GetStockLocationQuery,
)
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.presentation.stock_location.depends import (
    GetStockLocationHandlerDep,
)
from src.modules.inventory.presentation.stock_location.http.response.get_stock_location import (
    GetStockLocationResponse,
)


async def get_stock_location(
    warehouse_id: UUID,
    location_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetStockLocationHandlerDep,
) -> GetStockLocationResponse:
    """Читает карточку только в указанном складе текущего tenant."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetStockLocationQuery(
                warehouse_id=WarehouseIdVO.from_value(warehouse_id),
                location_id=StockLocationIdVO.from_value(location_id),
            )
        )
    except StockLocationNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetStockLocationResponse.from_dto(result)
