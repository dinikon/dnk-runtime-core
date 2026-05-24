from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from src.modules.communication.application.outbound_message import (
    GetOutboundMessageQuery,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.presentation.depends.application import (
    GetOutboundMessageUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.outbound_message.controller.error_mapper import (
    map_outbound_http_error,
)
from src.modules.communication.presentation.http.outbound_message.responses import (
    OutboundMessageResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get(
    "/messages/{outbound_message_id}",
    response_model=OutboundMessageResponseSchema,
)
async def get_message(
    outbound_message_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetOutboundMessageUseCaseDep,
) -> OutboundMessageResponseSchema:
    """HTTP controller получения outbound message."""
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            GetOutboundMessageQuery(
                tenant_id=EntityIdVO.from_value(tenant_id),
                outbound_message_id=OutboundMessageIdVO.from_value(outbound_message_id),
            )
        )
    except Exception as exc:
        raise map_outbound_http_error(exc) from exc
    return OutboundMessageResponseSchema(
        outbound_message_id=result.outbound_message_id,
        tenant_id=result.tenant_id,
        communication_request_id=result.communication_request_id,
        provider_connection_id=result.provider_connection_id,
        channel_code=result.channel_code,
        contact_id=result.contact_id,
        recipient_address=result.recipient_address,
        rendered_payload=dict(result.rendered_payload),
        provider_request_payload=dict(result.provider_request_payload),
        external_message_id=result.external_message_id,
        external_status=result.external_status,
        internal_status=result.internal_status,
        error_code=result.error_code,
        error_message=result.error_message,
        queued_at=result.queued_at,
        sent_at=result.sent_at,
        delivered_at=result.delivered_at,
        failed_at=result.failed_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


__all__ = ["get_message", "router"]
