from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product.query.get_product.query import (
    GetProductQuery,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductLocaleError,
    ProductNotFoundError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.presentation.product.depends import GetProductHandlerDep
from src.modules.catalog.presentation.product.http.response.get_product import (
    GetProductResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_product(
    product_id: UUID,
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: GetProductHandlerDep,
) -> GetProductResponse:
    """Читает только явно запрошенный язык без fallback."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetProductQuery(
                product_id=ProductIdVO.from_value(product_id),
                locale=ProductLocaleVO(locale),
            )
        )
    except InvalidProductLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ProductNotFoundError, ProductSkuNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetProductResponse.from_dto(result)
