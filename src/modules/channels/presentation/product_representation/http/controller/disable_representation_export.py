from uuid import UUID
from src.modules.channels.application.product_representation.command.disable_representation_export.command import (
    DisableRepresentationExportCommand,
)
from src.modules.channels.presentation.product_representation.depends import (
    DisableRepresentationExportHandlerDep,
)
from src.modules.channels.presentation.product_representation.http.request.disable_representation_export import (
    DisableRepresentationExportRequest,
)
from src.modules.channels.presentation.product_representation.http.response.disable_representation_export import (
    DisableRepresentationExportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def disable_representation_export(
    channel_id: UUID,
    group_id: UUID,
    payload: DisableRepresentationExportRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: DisableRepresentationExportHandlerDep,
) -> DisableRepresentationExportResponse:
    """Авторизует управление и явно преобразует HTTP в disable_representation_export."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        DisableRepresentationExportCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            group_id=group_id,
            expected_revision=payload.expected_revision,
            expected_binding_revision=payload.expected_binding_revision,
            expected_config_revision=payload.expected_config_revision,
        )
    )
    return DisableRepresentationExportResponse.from_dto(result)
