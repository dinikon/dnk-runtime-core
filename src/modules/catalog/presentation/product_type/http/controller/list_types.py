from fastapi import HTTPException

from src.modules.catalog.application.product_type.query.list_product_types.query import (
    ListProductTypesQuery,
)
from src.modules.catalog.domain.product_type.error import (
    ProductTypeNotFoundError,
    ProductTypeConflictError,
    InvalidProductTypeError,
)
from src.modules.catalog.presentation.product_type.depends import (
    ListProductTypesHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.response.list_type import (
    ListTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_types(
    context: AuthenticatedRequestContextDep,
    handler: ListProductTypesHandlerDep,
) -> list[ListTypeResponse]:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    items = await handler.execute(ListProductTypesQuery())
    return [ListTypeResponse.from_dto(item) for item in items]
