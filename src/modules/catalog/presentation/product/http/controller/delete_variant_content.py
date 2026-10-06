from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product.command.delete_variant_content.command import (
    DeleteVariantContentCommand,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductLocaleError,
    ProductNotFoundError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.presentation.product.depends import (
    DeleteVariantContentHandlerDep,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def delete_variant_content(
    product_id: UUID,
    variant_id: UUID,
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: DeleteVariantContentHandlerDep,
) -> None:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteVariantContentCommand(
                ProductIdVO.from_value(product_id),
                VariantIdVO.from_value(variant_id),
                locale,
                EntityIdVO.from_value(context.principal.user_id),
            )
        )
    except (ProductNotFoundError, ProductVariantNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidProductLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
