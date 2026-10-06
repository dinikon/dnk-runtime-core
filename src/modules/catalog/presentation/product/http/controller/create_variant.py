from uuid import UUID
from fastapi import HTTPException

from src.modules.catalog.application.product.command.create_variant.command import (
    CreateVariantCommand,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
    ProductNotFoundError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.presentation.product.depends import CreateVariantHandlerDep
from src.modules.catalog.presentation.product.http.request.create_variant import (
    CreateVariantRequest,
)
from src.modules.catalog.presentation.product.http.response.create_variant import (
    CreateVariantResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_variant(
    product_id: UUID,
    payload: CreateVariantRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateVariantHandlerDep,
) -> CreateVariantResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateVariantCommand(
                ProductIdVO.from_value(product_id),
                EntityIdVO.from_value(context.principal.user_id),
                payload.sku_id,
            )
        )
    except (ProductNotFoundError, ProductSkuNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidProductVariantError as exc:
        raise HTTPException(409, str(exc)) from exc
    return CreateVariantResponse.from_dto(result)
