from dataclasses import asdict
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
    CatalogDependencyUnavailableError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.application.product.query.get_product.query import (
    GetProductQuery,
)
from src.modules.catalog.presentation.product.depends import GetProductHandlerDep
from src.modules.catalog.presentation.product.http.response.get_product import (
    GetProductResponse,
)


async def get_product(
    context: AuthenticatedRequestContextDep,
    handler: GetProductHandlerDep,
    product_id: UUID,
    locale: str = Query(min_length=2, max_length=64),
) -> GetProductResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        query = GetProductQuery(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            product_id=ProductIdVO.from_value(product_id),
            locale=locale,
        )
        result = await handler.execute(query)
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogDependencyUnavailableError as exc:
        raise HTTPException(422, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    return GetProductResponse(**asdict(result))
