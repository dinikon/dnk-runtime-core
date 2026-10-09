from fastapi import HTTPException

from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
)
from src.modules.warehousing.domain.warehouse.error import (
    InvalidWarehouseCodeError,
    InvalidWarehouseTitleError,
    InvalidWarehouseTypeError,
    InvalidWarehouseTimezoneError,
    WarehouseCodeAlreadyExistsError,
)
from src.modules.warehousing.presentation.warehouse.depends import (
    CreateWarehouseHandlerDep,
)
from src.modules.warehousing.presentation.warehouse.http.request.create_warehouse import (
    CreateWarehouseRequest,
)
from src.modules.warehousing.presentation.warehouse.http.response.create_warehouse import (
    CreateWarehouseResponse,
)


async def create_warehouse(
    payload: CreateWarehouseRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: CreateWarehouseHandlerDep,
) -> CreateWarehouseResponse:
    """Проверяет права, создаёт команду из доверенного контекста и возвращает POST-ответ."""
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
        action="create",
        resource_type="warehouse",
    ):
        raise HTTPException(
            403,
            {"code": "warehouse.forbidden", "message": "Создание склада запрещено."},
        )
    command = CreateWarehouseCommand(
        tenant_id=tenant_id,
        actor_id=actor_id,
        code=payload.code,
        title=payload.title,
        warehouse_type=payload.type,
        timezone=payload.policy.timezone,
    )
    try:
        result = await handler.execute(command)
    except (
        InvalidWarehouseCodeError,
        InvalidWarehouseTitleError,
        InvalidWarehouseTypeError,
        InvalidWarehouseTimezoneError,
    ) as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    except WarehouseCodeAlreadyExistsError as exc:
        raise HTTPException(409, {"code": exc.code, "message": str(exc)}) from exc
    return CreateWarehouseResponse.from_dto(result)
