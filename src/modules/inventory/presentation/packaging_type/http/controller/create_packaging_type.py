from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.packaging_type.command.create_packaging_type.command import (
    CreatePackagingTypeCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeCodeAlreadyExistsError,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    CreatePackagingTypeHandlerDep,
)
from src.modules.inventory.presentation.packaging_type.http.request.create_packaging_type import (
    CreatePackagingTypeRequest,
)
from src.modules.inventory.presentation.packaging_type.http.response.create_packaging_type import (
    CreatePackagingTypeResponse,
)


async def create_packaging_type(
    payload: CreatePackagingTypeRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreatePackagingTypeHandlerDep,
) -> CreatePackagingTypeResponse:
    """Передаёт ручной ввод в Domain-сценарий и переводит ожидаемые отказы в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreatePackagingTypeCommand(code=payload.code, name=payload.name)
        )
    except PackagingTypeCodeAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreatePackagingTypeResponse.from_dto(result)
