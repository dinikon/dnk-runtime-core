from uuid import UUID
from fastapi import HTTPException

from src.modules.catalog.application.product.command.put_variant.command import (
    PutVariantCommand,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
    ProductNotFoundError,
    ProductSkuNotFoundError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.presentation.product.depends import PutVariantHandlerDep
from src.modules.catalog.presentation.product.http.request.put_variant import (
    PutVariantRequest,
)
from src.modules.catalog.presentation.product.http.response.put_variant import (
    PutVariantResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_variant(
    product_id: UUID,
    variant_id: UUID,
    payload: PutVariantRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutVariantHandlerDep,
) -> PutVariantResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutVariantCommand(
                ProductIdVO.from_value(product_id),
                VariantIdVO.from_value(variant_id),
                EntityIdVO.from_value(context.principal.user_id),
                payload.sku_id,
            )
        )
    except (
        ProductNotFoundError,
        ProductSkuNotFoundError,
        ProductVariantNotFoundError,
    ) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidProductVariantError as exc:
        raise HTTPException(409, str(exc)) from exc
    return PutVariantResponse.from_dto(result)
