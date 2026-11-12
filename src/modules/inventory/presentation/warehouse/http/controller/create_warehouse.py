from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.warehouse.error import WarehouseCodeAlreadyExistsError
from src.modules.inventory.presentation.warehouse.depends import (
    CreateWarehouseHandlerDep,
)
from src.modules.inventory.presentation.warehouse.http.request.create_warehouse import (
    CreateWarehouseRequest,
)
from src.modules.inventory.presentation.warehouse.http.response.create_warehouse import (
    CreateWarehouseResponse,
)


async def create_warehouse(
    payload: CreateWarehouseRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateWarehouseHandlerDep,
) -> CreateWarehouseResponse:
    """Передаёт ручные значения в сценарий создания и переводит ожидаемые ошибки."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateWarehouseCommand(code=payload.code, name=payload.name)
        )
    except WarehouseCodeAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateWarehouseResponse.from_dto(result)
