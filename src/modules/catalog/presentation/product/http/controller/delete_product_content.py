from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product.command.delete_product_content.command import (
    DeleteProductContentCommand,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductLocaleError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.presentation.product.depends import (
    DeleteProductContentHandlerDep,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def delete_product_content(
    product_id: UUID,
    locale: str,
    context: AuthenticatedRequestContextDep,
    handler: DeleteProductContentHandlerDep,
) -> None:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteProductContentCommand(
                ProductIdVO.from_value(product_id),
                locale,
                EntityIdVO.from_value(context.principal.user_id),
            )
        )
    except ProductNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidProductLocaleError as exc:
        raise HTTPException(422, str(exc)) from exc
