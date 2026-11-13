from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Query

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.query import (
    ListStockLocationsQuery,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.presentation.stock_location.depends import (
    ListStockLocationsHandlerDep,
)
from src.modules.inventory.presentation.stock_location.http.request.list_stock_locations import (
    ListStockLocationsRequest,
)
from src.modules.inventory.presentation.stock_location.http.response.list_stock_locations import (
    ListStockLocationsResponse,
)


async def list_stock_locations(
    warehouse_id: UUID,
    params: Annotated[ListStockLocationsRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListStockLocationsHandlerDep,
) -> ListStockLocationsResponse:
    """Передаёт проверенные схемой фильтры в сценарий плоского списка."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListStockLocationsQuery(
                warehouse_id=WarehouseIdVO.from_value(warehouse_id),
                offset=params.offset,
                limit=params.limit,
                search=params.search,
                is_active=params.is_active,
                location_type=params.location_type,
                parent_location_id=(
                    StockLocationIdVO.from_value(params.parent_location_id)
                    if params.parent_location_id is not None
                    else None
                ),
            )
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ListStockLocationsResponse.from_dto(result)
