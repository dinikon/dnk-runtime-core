from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.channels.application.product_representation.query.list_catalog_candidates.query import (
    ListCatalogCandidatesQuery,
)
from src.modules.channels.presentation.product_representation.depends import (
    ListCatalogCandidatesHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.product_representation.http.response.list_catalog_candidates import (
    ListCatalogCandidatesResponse,
)


async def list_catalog_candidates(
    publication_id: UUID,
    context: CatalogLinkContextDep,
    handler: ListCatalogCandidatesHandlerDep,
    locale: str = Query(min_length=1, max_length=80),
    search: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ListCatalogCandidatesResponse:
    """Преобразует HTTP list_catalog_candidates в конкретный use case доверенного tenant."""
    try:
        request = ListCatalogCandidatesQuery(
            UUID(context.principal.tenant_id),
            publication_id,
            locale,
            search,
            offset,
            limit,
        )
        result = await handler.execute(request)
        return ListCatalogCandidatesResponse(**asdict(result))
    except ChannelsError as error:
        raise http_error(error) from error
