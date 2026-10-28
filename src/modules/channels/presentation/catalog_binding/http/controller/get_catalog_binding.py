from uuid import UUID
from fastapi import Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    GetCatalogBindingHandlerDep,
)
from src.modules.channels.application.catalog_binding.query.get_catalog_binding.query import (
    GetCatalogBindingQuery,
)
from src.modules.channels.presentation.catalog_binding.http.response.get_catalog_binding import (
    GetCatalogBindingResponse,
)


async def get_catalog_binding(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetCatalogBindingHandlerDep,
    channel_id: UUID,
    group_id: UUID,
    locale: str = Query(default="uk", min_length=2, max_length=35),
) -> GetCatalogBindingResponse:
    """Авторизует и явно преобразует сценарий get_catalog_binding."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "read", channel_id
    )
    result = await handler.execute(
        GetCatalogBindingQuery(channel_id=channel_id, group_id=group_id, locale=locale)
    )
    return GetCatalogBindingResponse.model_validate(result)
