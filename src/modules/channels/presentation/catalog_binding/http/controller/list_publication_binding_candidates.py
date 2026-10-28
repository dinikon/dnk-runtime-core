from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    ListPublicationBindingCandidatesHandlerDep,
)
from src.modules.channels.application.catalog_binding.query.list_publication_binding_candidates.query import (
    ListPublicationBindingCandidatesQuery,
)
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.presentation.catalog_binding.http.response.list_publication_binding_candidates import (
    ListPublicationBindingCandidatesResponse,
)


async def list_publication_binding_candidates(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListPublicationBindingCandidatesHandlerDep,
    channel_id: UUID,
    mode: BindingMode,
    locale: str = Query(default="uk", min_length=2, max_length=35),
    search: str = Query(default="", max_length=255),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> ListPublicationBindingCandidatesResponse:
    """Авторизует и явно преобразует сценарий list_publication_binding_candidates."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "read", channel_id
    )
    result = await handler.execute(
        ListPublicationBindingCandidatesQuery(
            channel_id=channel_id,
            mode=mode,
            locale=locale,
            search=search,
            offset=offset,
            limit=limit,
        )
    )
    return ListPublicationBindingCandidatesResponse.model_validate(result)
