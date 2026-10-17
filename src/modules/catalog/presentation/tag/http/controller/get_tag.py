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
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.application.tag.query.get_tag.query import (
    GetTagQuery,
)
from src.modules.catalog.presentation.tag.depends import GetTagHandlerDep
from src.modules.catalog.presentation.tag.http.response.get_tag import (
    GetTagResponse,
)


async def get_tag(
    context: AuthenticatedRequestContextDep,
    handler: GetTagHandlerDep,
    tag_id: UUID,
    locale: str = Query(min_length=2, max_length=64),
) -> GetTagResponse:
    """Преобразует явный HTTP-контракт get_tag и доверенный Identity context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetTagQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                tag_id=TagIdVO.from_value(tag_id),
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
    return GetTagResponse(**asdict(result))
