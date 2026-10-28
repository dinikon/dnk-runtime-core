from uuid import UUID
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    CreateCatalogBindingHandlerDep,
)
from src.modules.channels.application.catalog_binding.command.create_catalog_binding.command import (
    CreateCatalogBindingCommand,
)
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO
from src.modules.channels.presentation.catalog_binding.http.request.create_catalog_binding import (
    CreateCatalogBindingRequest,
)
from src.modules.channels.presentation.catalog_binding.http.response.create_catalog_binding import (
    CreateCatalogBindingResponse,
)


async def create_catalog_binding(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: CreateCatalogBindingHandlerDep,
    channel_id: UUID,
    payload: CreateCatalogBindingRequest,
) -> CreateCatalogBindingResponse:
    """Авторизует и явно преобразует сценарий create_catalog_binding."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        CreateCatalogBindingCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            catalog_root_id=payload.catalog_root_id,
            mode=payload.mode,
            publication_root_id=payload.publication_root_id,
            items=tuple(
                BindingPairDTO(v.catalog_position_id, v.publication_id)
                for v in payload.items
            ),
            catalog_token=payload.catalog_token,
            publication_token=payload.publication_token,
            locale=payload.locale,
        )
    )
    return CreateCatalogBindingResponse.model_validate(result)
