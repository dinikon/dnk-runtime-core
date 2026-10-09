from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.warehousing.domain.warehouse.error import WarehouseNotFoundError
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.presentation.warehouse.depends import (
    GetWarehouseHandlerDep,
)
from src.modules.warehousing.presentation.warehouse.http.response.get_warehouse import (
    GetWarehouseResponse,
)


async def get_warehouse(
    warehouse_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetWarehouseHandlerDep,
) -> GetWarehouseResponse:
    """Проверяет права на конкретный склад и переводит проекцию в HTTP-карточку."""
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
        action="read",
        resource_type="warehouse",
        resource_id=warehouse_id,
    ):
        raise HTTPException(
            403, {"code": "warehouse.forbidden", "message": "Чтение склада запрещено."}
        )
    try:
        result = await handler.execute(
            GetWarehouseQuery(
                tenant_id=tenant_id, warehouse_id=WarehouseIdVO.from_value(warehouse_id)
            )
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(404, {"code": exc.code, "message": str(exc)}) from exc
    return GetWarehouseResponse.from_dto(result)
