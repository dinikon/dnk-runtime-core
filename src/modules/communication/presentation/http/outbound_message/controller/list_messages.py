from __future__ import annotations

from fastapi import APIRouter

from src.modules.communication.application.outbound_message import (
    ListOutboundMessagesQuery,
)
from src.modules.communication.presentation.depends.application import (
    ListOutboundMessagesUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.outbound_message.controller.error_mapper import (
    map_outbound_http_error,
)
from src.modules.communication.presentation.http.outbound_message.responses import (
    ListOutboundMessagesResponseSchema,
    OutboundMessageResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get("/messages", response_model=ListOutboundMessagesResponseSchema)
async def list_messages(
    context: AuthenticatedRequestContextDep,
    use_case: ListOutboundMessagesUseCaseDep,
    limit: int = 100,
    offset: int = 0,
) -> ListOutboundMessagesResponseSchema:
    """HTTP controller списка outbound messages."""
    tenant_id = require_tenant_id(context)
    try:
        items = await use_case(
            ListOutboundMessagesQuery(
                tenant_id=EntityIdVO.from_value(tenant_id),
                limit=limit,
                offset=offset,
            )
        )
    except Exception as exc:
        raise map_outbound_http_error(exc) from exc
    return ListOutboundMessagesResponseSchema(
        items=[
            OutboundMessageResponseSchema(
                outbound_message_id=item.outbound_message_id,
                tenant_id=item.tenant_id,
                communication_request_id=item.communication_request_id,
                provider_connection_id=item.provider_connection_id,
                channel_code=item.channel_code,
                contact_id=item.contact_id,
                recipient_address=item.recipient_address,
                rendered_payload=dict(item.rendered_payload),
                provider_request_payload=dict(item.provider_request_payload),
                external_message_id=item.external_message_id,
                external_status=item.external_status,
                internal_status=item.internal_status,
                error_code=item.error_code,
                error_message=item.error_message,
                queued_at=item.queued_at,
                sent_at=item.sent_at,
                delivered_at=item.delivered_at,
                failed_at=item.failed_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


__all__ = ["list_messages", "router"]
