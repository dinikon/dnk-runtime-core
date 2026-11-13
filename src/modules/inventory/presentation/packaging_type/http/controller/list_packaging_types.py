from typing import Annotated

from fastapi import HTTPException, Query

from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.query import (
    ListPackagingTypesQuery,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    ListPackagingTypesHandlerDep,
)
from src.modules.inventory.presentation.packaging_type.http.request.list_packaging_types import (
    ListPackagingTypesRequest,
)
from src.modules.inventory.presentation.packaging_type.http.response.list_packaging_types import (
    ListPackagingTypesResponse,
)


async def list_packaging_types(
    params: Annotated[ListPackagingTypesRequest, Query()],
    context: AuthenticatedRequestContextDep,
    handler: ListPackagingTypesHandlerDep,
) -> ListPackagingTypesResponse:
    """Передаёт проверенные схемой фильтры и явно формирует HTTP-страницу."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(
        ListPackagingTypesQuery(
            offset=params.offset,
            limit=params.limit,
            search=params.search,
            is_active=params.is_active,
        )
    )
    return ListPackagingTypesResponse.from_dto(result)
