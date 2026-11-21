from uuid import UUID

from fastapi import HTTPException, Response

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.packaging_type.command.delete_packaging_type.command import (
    DeletePackagingTypeCommand,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeInUseError,
    PackagingTypeNotFoundError,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    DeletePackagingTypeHandlerDep,
)


async def delete_packaging_type(
    packaging_type_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeletePackagingTypeHandlerDep,
) -> Response:
    """Удаляет неиспользуемый тип по ID и возвращает пустой 204 либо ожидаемый отказ."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeletePackagingTypeCommand(PackagingTypeIdVO.from_value(packaging_type_id))
        )
    except PackagingTypeNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PackagingTypeInUseError as exc:
        raise HTTPException(409, str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(status_code=204)
