from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.warehouse.command.update_warehouse.command import (
    UpdateWarehouseCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.warehouse.error import (
    WarehouseNotFoundError,
    WarehouseCodeAlreadyExistsError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.presentation.warehouse.depends import (
    UpdateWarehouseHandlerDep,
)
from src.modules.inventory.presentation.warehouse.http.request.patch_warehouse import (
    PatchWarehouseRequest,
)
from src.modules.inventory.presentation.warehouse.http.response.patch_warehouse import (
    PatchWarehouseResponse,
)


async def patch_warehouse(
    warehouse_id: UUID,
    payload: PatchWarehouseRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateWarehouseHandlerDep,
) -> PatchWarehouseResponse:
    """Преобразует PATCH в команду и переводит ожидаемые отказы в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateWarehouseCommand(
                warehouse_id=WarehouseIdVO(warehouse_id),
                fields=frozenset(payload.model_fields_set),
                code=payload.code,
                name=payload.name,
                is_active=payload.is_active,
            )
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except WarehouseCodeAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchWarehouseResponse.from_dto(result)
