from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product_type.query.get_product_type.query import (
    GetProductTypeQuery,
)
from src.modules.catalog.domain.product_type.error import (
    ProductTypeNotFoundError,
    ProductTypeConflictError,
    InvalidProductTypeError,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.presentation.product_type.depends import (
    GetProductTypeHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.response.get_type import (
    GetTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_type(
    type_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetProductTypeHandlerDep,
) -> GetTypeResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        item = await handler.execute(
            GetProductTypeQuery(ProductTypeIdVO.from_value(type_id))
        )
    except ProductTypeNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetTypeResponse.from_dto(item)
