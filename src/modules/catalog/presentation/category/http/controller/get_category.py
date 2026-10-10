from dataclasses import asdict
from uuid import UUID
from fastapi import HTTPException, Query
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.application.category.query.get_category.query import (
    GetCategoryQuery,
)
from src.modules.catalog.presentation.category.depends import GetCategoryHandlerDep
from src.modules.catalog.presentation.category.http.response.get_category import (
    GetCategoryResponse,
)


async def get_category(
    context: AuthenticatedRequestContextDep,
    handler: GetCategoryHandlerDep,
    category_id: UUID,
    locale: str = Query(min_length=2, max_length=64),
) -> GetCategoryResponse:
    """Преобразует явный HTTP-контракт get_category и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetCategoryQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                category_id=CategoryIdVO.from_value(category_id),
                locale=locale,
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"23505", "23503"}:
            raise HTTPException(
                409, "Код уже существует или объект используется."
            ) from exc
        raise
    return GetCategoryResponse(**asdict(result))
