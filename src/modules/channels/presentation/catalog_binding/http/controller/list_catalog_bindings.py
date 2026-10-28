from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    ListCatalogBindingsHandlerDep,
)
from src.modules.channels.application.catalog_binding.query.list_catalog_bindings.query import (
    ListCatalogBindingsQuery,
)
from src.modules.channels.presentation.catalog_binding.http.response.list_catalog_bindings import (
    ListCatalogBindingsResponse,
)


async def list_catalog_bindings(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListCatalogBindingsHandlerDep,
    catalog_item_id: UUID | None = None,
    channel_id: UUID | None = None,
    publication_id: UUID | None = None,
    mode: BindingMode | None = None,
    locale: str = Query(default="uk", min_length=2, max_length=35),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> ListCatalogBindingsResponse:
    """Авторизует и явно преобразует сценарий list_catalog_bindings."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "read", channel_id
    )
    result = await handler.execute(
        ListCatalogBindingsQuery(
            catalog_root_id=catalog_item_id,
            mode=mode,
            channel_id=channel_id,
            publication_id=publication_id,
            locale=locale,
            offset=offset,
            limit=limit,
        )
    )
    return ListCatalogBindingsResponse.model_validate(result)
