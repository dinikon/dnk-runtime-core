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
    outbound_message_response,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep

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
    return outbound_message_response(result)


__all__ = ["get_message", "router"]
