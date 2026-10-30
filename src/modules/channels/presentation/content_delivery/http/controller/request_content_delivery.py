from uuid import UUID
from src.modules.channels.application.content_delivery.command.request_content_delivery.command import (
    RequestContentDeliveryCommand,
)
from src.modules.channels.presentation.content_delivery.depends import (
    RequestContentDeliveryHandlerDep,
)
from src.modules.channels.presentation.content_delivery.http.response.request_content_delivery import (
    RequestContentDeliveryResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_delivery.http.request.request_content_delivery import (
    RequestContentDeliveryRequest,
)


async def request_content_delivery(
    channel_id: UUID,
    group_id: UUID,
    payload: RequestContentDeliveryRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RequestContentDeliveryHandlerDep,
) -> RequestContentDeliveryResponse:
    """Авторизует сценарий и явно преобразует HTTP-контракт в Application."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        RequestContentDeliveryCommand(
            tenant_id=tenant_id,
            channel_id=channel_id,
            group_id=group_id,
            actor_id=actor_id,
            expected_revision=payload.expected_revision,
            expected_binding_revision=payload.expected_binding_revision,
            expected_config_revision=payload.expected_config_revision,
            fingerprint=payload.content_fingerprint,
        )
    )
    return RequestContentDeliveryResponse.from_dto(result)
