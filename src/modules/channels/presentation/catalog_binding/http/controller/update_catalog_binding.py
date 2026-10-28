from uuid import UUID
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    UpdateCatalogBindingHandlerDep,
)
from src.modules.channels.application.catalog_binding.command.update_catalog_binding.command import (
    UpdateCatalogBindingCommand,
)
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO
from src.modules.channels.presentation.catalog_binding.http.request.update_catalog_binding import (
    UpdateCatalogBindingRequest,
)
from src.modules.channels.presentation.catalog_binding.http.response.update_catalog_binding import (
    UpdateCatalogBindingResponse,
)


async def update_catalog_binding(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: UpdateCatalogBindingHandlerDep,
    channel_id: UUID,
    group_id: UUID,
    payload: UpdateCatalogBindingRequest,
) -> UpdateCatalogBindingResponse:
    """Авторизует и явно преобразует сценарий update_catalog_binding."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        UpdateCatalogBindingCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            group_id=group_id,
            expected_revision=payload.expected_revision,
            items=tuple(
                BindingPairDTO(v.catalog_position_id, v.publication_id)
                for v in payload.items
            ),
            catalog_token=payload.catalog_token,
            publication_token=payload.publication_token,
            locale=payload.locale,
        )
    )
    return UpdateCatalogBindingResponse.model_validate(result)
