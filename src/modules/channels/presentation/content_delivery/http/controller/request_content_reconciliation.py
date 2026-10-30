from uuid import UUID
from src.modules.channels.application.content_delivery.command.request_content_reconciliation.command import (
    RequestContentReconciliationCommand,
)
from src.modules.channels.presentation.content_delivery.depends import (
    RequestContentReconciliationHandlerDep,
)
from src.modules.channels.presentation.content_delivery.http.response.request_content_reconciliation import (
    RequestContentReconciliationResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_delivery.http.request.request_content_reconciliation import (
    RequestContentReconciliationRequest,
)


async def request_content_reconciliation(
    channel_id: UUID,
    group_id: UUID,
    publication_id: UUID,
    payload: RequestContentReconciliationRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RequestContentReconciliationHandlerDep,
) -> RequestContentReconciliationResponse:
    """Авторизует сценарий и явно преобразует HTTP-контракт в Application."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        RequestContentReconciliationCommand(
            tenant_id=tenant_id,
            channel_id=channel_id,
            group_id=group_id,
            actor_id=actor_id,
            publication_id=publication_id,
            expected_revision=payload.expected_revision,
        )
    )
    return RequestContentReconciliationResponse.from_dto(result)
