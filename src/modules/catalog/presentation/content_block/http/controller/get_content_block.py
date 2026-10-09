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
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.application.content_block.query.get_content_block.query import (
    GetContentBlockQuery,
)
from src.modules.catalog.presentation.content_block.depends import (
    GetContentBlockHandlerDep,
)
from src.modules.catalog.presentation.content_block.http.response.get_content_block import (
    GetContentBlockResponse,
)


async def get_content_block(
    context: AuthenticatedRequestContextDep,
    handler: GetContentBlockHandlerDep,
    content_block_id: UUID,
    locale: str = Query(min_length=2, max_length=64),
) -> GetContentBlockResponse:
    """Преобразует доверенный контекст и конкретный HTTP-контракт в сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        query = GetContentBlockQuery(
            tenant_id=EntityIdVO.from_value(principal.tenant_id),
            content_block_id=ContentBlockIdVO.from_value(content_block_id),
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
    return GetContentBlockResponse(**asdict(result))
