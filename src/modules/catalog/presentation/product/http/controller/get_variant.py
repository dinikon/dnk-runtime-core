from uuid import UUID
from fastapi import HTTPException

from src.modules.catalog.application.product.query.get_variant.query import (
    GetVariantQuery,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductLocaleError,
    ProductNotFoundError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.presentation.product.depends import GetVariantHandlerDep
from src.modules.catalog.presentation.product.http.response.get_variant import (
    GetVariantResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_variant(
    product_id: UUID,
    variant_id: UUID,
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: GetVariantHandlerDep,
) -> GetVariantResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetVariantQuery(
                ProductIdVO.from_value(product_id),
                VariantIdVO.from_value(variant_id),
                ProductLocaleVO(locale),
            )
        )
    except InvalidProductLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ProductNotFoundError, ProductSkuNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetVariantResponse.from_dto(result)
