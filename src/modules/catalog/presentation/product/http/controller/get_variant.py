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
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.application.product.query.get_variant.query import (
    GetVariantQuery,
)
from src.modules.catalog.presentation.product.depends import GetVariantHandlerDep
from src.modules.catalog.presentation.product.http.response.get_variant import (
    GetVariantResponse,
)


async def get_variant(
    context: AuthenticatedRequestContextDep,
    handler: GetVariantHandlerDep,
    product_id: UUID,
    variant_id: UUID,
    locale: str = Query(min_length=2, max_length=64),
) -> GetVariantResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        query = GetVariantQuery(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            product_id=ProductIdVO.from_value(product_id),
            variant_id=VariantIdVO.from_value(variant_id),
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
    return GetVariantResponse(**asdict(result))
