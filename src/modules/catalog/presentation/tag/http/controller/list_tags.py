from dataclasses import asdict
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
from src.modules.catalog.application.tag.query.list_tags.query import (
    ListTagsQuery,
)
from src.modules.catalog.presentation.tag.depends import ListTagsHandlerDep
from src.modules.catalog.presentation.tag.http.response.list_tags import (
    ListTagsResponse,
)


async def list_tags(
    context: AuthenticatedRequestContextDep,
    handler: ListTagsHandlerDep,
    locale: str = Query(min_length=2, max_length=64),
    search: str = Query(default="", max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ListTagsResponse:
    """Преобразует явный HTTP-контракт list_tags и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ListTagsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                locale=locale,
                search=search,
                page=page,
                page_size=page_size,
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
    return ListTagsResponse(**asdict(result))
