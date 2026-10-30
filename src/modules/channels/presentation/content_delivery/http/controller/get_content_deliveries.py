from uuid import UUID
from src.modules.channels.application.content_delivery.query.get_content_deliveries.query import (
    GetContentDeliveriesQuery,
)
from src.modules.channels.presentation.content_delivery.depends import (
    GetContentDeliveriesHandlerDep,
)
from src.modules.channels.presentation.content_delivery.http.response.get_content_deliveries import (
    GetContentDeliveriesResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_content_deliveries(
    channel_id: UUID,
    group_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetContentDeliveriesHandlerDep,
) -> GetContentDeliveriesResponse:
    """Авторизует сценарий и явно преобразует HTTP-контракт в Application."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "read", channel_id
    )
    result = await handler.execute(
        GetContentDeliveriesQuery(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
    )
    return GetContentDeliveriesResponse.from_dto(result)
