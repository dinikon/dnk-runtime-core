from uuid import UUID

from src.modules.channels.application.content_delivery.command.resolve_content_uncertainty.command import (
    ResolveContentUncertaintyCommand,
)
from src.modules.channels.presentation.content_delivery.depends import (
    ResolveContentUncertaintyHandlerDep,
)
from src.modules.channels.presentation.content_delivery.http.request.resolve_content_uncertainty import (
    ResolveContentUncertaintyRequest,
)
from src.modules.channels.presentation.content_delivery.http.response.resolve_content_uncertainty import (
    ResolveContentUncertaintyResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def resolve_content_uncertainty(
    channel_id: UUID,
    group_id: UUID,
    publication_id: UUID,
    payload: ResolveContentUncertaintyRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ResolveContentUncertaintyHandlerDep,
) -> ResolveContentUncertaintyResponse:
    """Авторизует решение оператора и передаёт конкретную команду Application."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        ResolveContentUncertaintyCommand(
            tenant_id=tenant_id,
            actor_id=actor_id,
            channel_id=channel_id,
            group_id=group_id,
            publication_id=publication_id,
            expected_revision=payload.expected_revision,
            acknowledge_unconfirmed=payload.acknowledge_unconfirmed,
        )
    )
    return ResolveContentUncertaintyResponse.from_dto(result)
