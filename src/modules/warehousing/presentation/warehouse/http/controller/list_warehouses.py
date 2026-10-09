from typing import Annotated

from fastapi import HTTPException, Query

from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListParametersError,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.warehousing.domain.warehouse.error import InvalidWarehouseTypeError
from src.modules.warehousing.presentation.warehouse.depends import (
    ListWarehousesHandlerDep,
)
from src.modules.warehousing.presentation.warehouse.http.response.list_warehouses import (
    ListWarehousesResponse,
)


async def list_warehouses(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListWarehousesHandlerDep,
    status: str | None = None,
    warehouse_type: Annotated[str | None, Query(alias="type")] = None,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ListWarehousesResponse:
    """Преобразует фильтры и доверенный tenant в query стабильного списка."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(
            403,
            {
                "code": "warehouse.tenant_required",
                "message": "Требуется tenant-контекст.",
            },
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    actor_id = EntityIdVO.from_value(principal.user_id)
    if not await authorization.can(
        user_id=actor_id.uuid,
        tenant_id=tenant_id.uuid,
        action="list",
        resource_type="warehouse",
    ):
        raise HTTPException(
            403,
            {"code": "warehouse.forbidden", "message": "Список складов недоступен."},
        )
    try:
        result = await handler.execute(
            ListWarehousesQuery(
                tenant_id=tenant_id,
                status=status,
                warehouse_type=warehouse_type,
                cursor=cursor,
                limit=limit,
            )
        )
    except (InvalidWarehouseListParametersError, InvalidWarehouseTypeError) as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    return ListWarehousesResponse.from_dto(result)
