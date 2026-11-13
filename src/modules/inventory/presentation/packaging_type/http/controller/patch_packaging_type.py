from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.packaging_type.command.update_packaging_type.command import (
    UpdatePackagingTypeCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeNotFoundError,
    PackagingTypeCodeAlreadyExistsError,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    UpdatePackagingTypeHandlerDep,
)
from src.modules.inventory.presentation.packaging_type.http.request.patch_packaging_type import (
    PatchPackagingTypeRequest,
)
from src.modules.inventory.presentation.packaging_type.http.response.patch_packaging_type import (
    PatchPackagingTypeResponse,
)


async def patch_packaging_type(
    packaging_type_id: UUID,
    payload: PatchPackagingTypeRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdatePackagingTypeHandlerDep,
) -> PatchPackagingTypeResponse:
    """Преобразует PATCH в команду и переводит ожидаемые отказы в HTTP."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdatePackagingTypeCommand(
                packaging_type_id=PackagingTypeIdVO(packaging_type_id),
                fields=frozenset(payload.model_fields_set),
                code=payload.code,
                name=payload.name,
                is_active=payload.is_active,
            )
        )
    except PackagingTypeNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PackagingTypeCodeAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchPackagingTypeResponse.from_dto(result)
