from uuid import UUID
from fastapi import HTTPException, Response

from src.modules.catalog.application.product.command.delete_variant.command import (
    DeleteVariantCommand,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
    ProductNotFoundError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.presentation.product.depends import DeleteVariantHandlerDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def delete_variant(
    product_id: UUID,
    variant_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteVariantHandlerDep,
) -> Response:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteVariantCommand(
                ProductIdVO.from_value(product_id),
                VariantIdVO.from_value(variant_id),
                EntityIdVO.from_value(context.principal.user_id),
            )
        )
    except (ProductNotFoundError, ProductVariantNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidProductVariantError as exc:
        raise HTTPException(409, str(exc)) from exc
    return Response(status_code=204)
