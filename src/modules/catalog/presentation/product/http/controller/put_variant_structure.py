from uuid import UUID
from fastapi import HTTPException

from src.modules.catalog.application.product.command.put_variant_structure.command import (
    PutVariantStructureCommand,
    VariantStructureItem,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
    ProductNotFoundError,
    ProductSkuNotFoundError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.presentation.product.depends import (
    PutVariantStructureHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.put_variant_structure import (
    PutVariantStructureRequest,
)
from src.modules.catalog.presentation.product.http.response.put_variant_structure import (
    PutVariantStructureResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_variant_structure(
    product_id: UUID,
    payload: PutVariantStructureRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutVariantStructureHandlerDep,
) -> PutVariantStructureResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutVariantStructureCommand(
                ProductIdVO.from_value(product_id),
                EntityIdVO.from_value(context.principal.user_id),
                payload.kind,
                tuple(
                    VariantStructureItem(item.sku_id, item.id)
                    for item in payload.variants
                ),
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
    return PutVariantStructureResponse.from_dto(result)
