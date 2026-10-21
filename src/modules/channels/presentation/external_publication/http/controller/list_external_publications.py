from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from typing import Literal
from src.modules.channels.application.external_publication.query.list_external_publications.query import (
    ListExternalPublicationsQuery,
)
from src.modules.channels.presentation.external_publication.depends import (
    ListExternalPublicationsHandlerDep,
)
from src.modules.channels.presentation.depends.access import ChannelsReadContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.external_publication.http.response.list_external_publications import (
    ListExternalPublicationsResponse,
)


async def list_external_publications(
    connection_id: UUID,
    context: ChannelsReadContextDep,
    handler: ListExternalPublicationsHandlerDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    stock_status: str | None = None,
    export_status: Literal["enabled", "disabled"] | None = None,
    binding_status: Literal["bound", "unbound"] | None = None,
    identity_status: (
        Literal["missing", "duplicate", "valid", "not_required"] | None
    ) = None,
    identity_key: str | None = Query(default=None, min_length=1, max_length=512),
) -> ListExternalPublicationsResponse:
    """Преобразует HTTP list_external_publications в отдельный Command/Query и безопасный ответ."""
    try:
        request = ListExternalPublicationsQuery(
            tenant_id=UUID(context.principal.tenant_id),
            connection_id=connection_id,
            offset=offset,
            limit=limit,
            search=search,
            stock_status=stock_status,
            export_status=export_status,
            binding_status=binding_status,
            identity_status=identity_status,
            identity_key=identity_key,
        )
        result = await handler.execute(request)
    except ChannelsError as error:
        raise http_error(error) from error
    return ListExternalPublicationsResponse(**asdict(result))
