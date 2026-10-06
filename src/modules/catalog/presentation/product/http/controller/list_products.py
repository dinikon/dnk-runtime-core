from fastapi import HTTPException

from src.modules.catalog.application.product.query.list_products.query import (
    ListProductsQuery,
)
from src.modules.catalog.domain.product.error import InvalidProductLocaleError
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.presentation.product.depends import ListProductsHandlerDep
from src.modules.catalog.presentation.product.http.response.list_products import (
    ListProductItemResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_products(
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: ListProductsHandlerDep,
) -> list[ListProductItemResponse]:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        results = await handler.execute(ListProductsQuery(ProductLocaleVO(locale)))
    except InvalidProductLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    return [ListProductItemResponse.from_dto(item) for item in results]
