from uuid import UUID
from src.modules.channels.application.product_representation.query.get_representation.query import (
    GetRepresentationQuery,
)
from src.modules.channels.presentation.product_representation.depends import (
    GetRepresentationHandlerDep,
)
from src.modules.channels.presentation.product_representation.http.response.get_representation import (
    GetRepresentationResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_representation(
    channel_id: UUID,
    group_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetRepresentationHandlerDep,
) -> GetRepresentationResponse:
    """Читает overrides после проверки tenant и права channels.read."""
    await channel_access(context, authorization, "read", channel_id)
    return GetRepresentationResponse.from_dto(
        await handler.execute(GetRepresentationQuery(channel_id, group_id))
    )
