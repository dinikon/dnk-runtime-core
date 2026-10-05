from uuid import UUID

from fastapi import HTTPException

from src.modules.catalog.application.product.command.put_product_categories.command import (
    PutProductCategoriesCommand,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductCategoriesError,
    ProductCategoryNotFoundError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.presentation.product.depends import (
    PutProductCategoriesHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.put_product_categories import (
    PutProductCategoriesRequest,
)
from src.modules.catalog.presentation.product.http.response.put_product_categories import (
    PutProductCategoriesResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def put_product_categories(
    product_id: UUID,
    payload: PutProductCategoriesRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutProductCategoriesHandlerDep,
) -> PutProductCategoriesResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutProductCategoriesCommand(
                ProductIdVO.from_value(product_id),
                EntityIdVO.from_value(principal.user_id),
                tuple(payload.category_ids),
                payload.primary_category_id,
            )
        )
    except InvalidProductCategoriesError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ProductCategoryNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    return PutProductCategoriesResponse.from_dto(result)
