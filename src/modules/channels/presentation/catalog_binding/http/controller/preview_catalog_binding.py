from uuid import UUID
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    PreviewCatalogBindingHandlerDep,
)
from src.modules.channels.application.catalog_binding.query.preview_catalog_binding.query import (
    PreviewCatalogBindingQuery,
)
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO
from src.modules.channels.presentation.catalog_binding.http.request.preview_catalog_binding import (
    PreviewCatalogBindingRequest,
)
from src.modules.channels.presentation.catalog_binding.http.response.preview_catalog_binding import (
    PreviewCatalogBindingResponse,
)


async def preview_catalog_binding(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: PreviewCatalogBindingHandlerDep,
    channel_id: UUID,
    payload: PreviewCatalogBindingRequest,
) -> PreviewCatalogBindingResponse:
    """Авторизует и явно преобразует сценарий preview_catalog_binding."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "read", channel_id
    )
    result = await handler.execute(
        PreviewCatalogBindingQuery(
            channel_id=channel_id,
            catalog_root_id=payload.catalog_root_id,
            mode=payload.mode,
            publication_root_id=payload.publication_root_id,
            items=tuple(
                BindingPairDTO(v.catalog_position_id, v.publication_id)
                for v in payload.items
            ),
            group_id=payload.group_id,
            locale=payload.locale,
        )
    )
    return PreviewCatalogBindingResponse.model_validate(result)
