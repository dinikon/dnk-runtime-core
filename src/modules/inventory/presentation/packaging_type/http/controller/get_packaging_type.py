from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.query import (
    GetPackagingTypeQuery,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    GetPackagingTypeHandlerDep,
)
from src.modules.inventory.presentation.packaging_type.http.response.get_packaging_type import (
    GetPackagingTypeResponse,
)


async def get_packaging_type(
    packaging_type_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetPackagingTypeHandlerDep,
) -> GetPackagingTypeResponse:
    """Читает конкретную карточку текущего tenant и переводит отсутствие в 404."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetPackagingTypeQuery(PackagingTypeIdVO.from_value(packaging_type_id))
        )
    except PackagingTypeNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetPackagingTypeResponse.from_dto(result)
