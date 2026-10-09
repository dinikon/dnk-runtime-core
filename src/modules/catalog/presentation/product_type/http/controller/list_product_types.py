from dataclasses import asdict
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
from src.modules.catalog.application.product_type.query.list_product_types.query import (
    ListProductTypesQuery,
)
from src.modules.catalog.presentation.product_type.depends import (
    ListProductTypesHandlerDep,
)
from src.modules.catalog.presentation.product_type.http.response.list_product_types import (
    ListProductTypesResponse,
)


async def list_product_types(
    context: AuthenticatedRequestContextDep,
    handler: ListProductTypesHandlerDep,
    locale: str = Query(min_length=2, max_length=64),
    search: str = Query(default="", max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ListProductTypesResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        query = ListProductTypesQuery(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            locale=locale,
            search=search,
            page=page,
            page_size=page_size,
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
    return ListProductTypesResponse(**asdict(result))
