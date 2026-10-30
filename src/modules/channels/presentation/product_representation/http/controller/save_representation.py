from uuid import UUID
from src.modules.channels.application.product_representation.command.save_representation.command import (
    SaveRepresentationCommand,
)
from src.modules.channels.presentation.product_representation.depends import (
    SaveRepresentationHandlerDep,
)
from src.modules.channels.presentation.product_representation.http.request.save_representation import (
    SaveRepresentationRequest,
)
from src.modules.channels.presentation.product_representation.http.response.save_representation import (
    SaveRepresentationResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def save_representation(
    channel_id: UUID,
    group_id: UUID,
    payload: SaveRepresentationRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: SaveRepresentationHandlerDep,
) -> SaveRepresentationResponse:
    """Авторизует управление и явно преобразует HTTP в save_representation."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        SaveRepresentationCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            group_id=group_id,
            expected_revision=payload.expected_revision,
            expected_binding_revision=payload.expected_binding_revision,
            expected_config_revision=payload.expected_config_revision,
            overrides=payload.overrides.to_value(),
        )
    )
    return SaveRepresentationResponse.from_dto(result)
