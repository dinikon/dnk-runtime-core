from uuid import UUID
from src.modules.channels.application.product_representation.command.enable_representation_export.command import (
    EnableRepresentationExportCommand,
)
from src.modules.channels.presentation.product_representation.depends import (
    EnableRepresentationExportHandlerDep,
)
from src.modules.channels.presentation.product_representation.http.request.enable_representation_export import (
    EnableRepresentationExportRequest,
)
from src.modules.channels.presentation.product_representation.http.response.enable_representation_export import (
    EnableRepresentationExportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def enable_representation_export(
    channel_id: UUID,
    group_id: UUID,
    payload: EnableRepresentationExportRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: EnableRepresentationExportHandlerDep,
) -> EnableRepresentationExportResponse:
    """Авторизует управление и явно преобразует HTTP в enable_representation_export."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        EnableRepresentationExportCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            group_id=group_id,
            expected_revision=payload.expected_revision,
            expected_binding_revision=payload.expected_binding_revision,
            expected_config_revision=payload.expected_config_revision,
        )
    )
    return EnableRepresentationExportResponse.from_dto(result)
