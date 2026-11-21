from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.presentation.warehouse.depends import GetWarehouseHandlerDep
from src.modules.inventory.presentation.warehouse.http.response.get_warehouse import (
    GetWarehouseResponse,
)


async def get_warehouse(
    warehouse_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetWarehouseHandlerDep,
) -> GetWarehouseResponse:
    """Читает карточку текущего tenant с явным преобразованием отсутствия в 404."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(GetWarehouseQuery(WarehouseIdVO(warehouse_id)))
    except WarehouseNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetWarehouseResponse.from_dto(result)
