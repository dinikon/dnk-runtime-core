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
    outbound_message_response,
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
        items=[outbound_message_response(item) for item in items]
    )


__all__ = ["list_messages", "router"]
