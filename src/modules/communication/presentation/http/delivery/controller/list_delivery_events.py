from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from src.modules.communication.application.delivery import ListDeliveryEventsQuery
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.presentation.depends.application import (
    ListDeliveryEventsUseCaseDep,
)
from src.modules.communication.presentation.http.common import (
    map_communication_http_error,
    require_tenant_id,
)
from src.modules.communication.presentation.http.delivery.responses import (
    DeliveryEventResponseSchema,
    ListDeliveryEventsResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get(
    "/messages/{outbound_message_id}/events",
    response_model=ListDeliveryEventsResponseSchema,
)
async def list_message_delivery_events(
    outbound_message_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryEventsUseCaseDep,
    limit: int = 100,
    offset: int = 0,
) -> ListDeliveryEventsResponseSchema:
    """HTTP controller списка delivery events по outbound message."""
    return await _list_delivery_events(
        context=context,
        use_case=use_case,
        limit=limit,
        offset=offset,
        outbound_message_id=outbound_message_id,
        external_message_id=None,
        internal_status=None,
        event_type=None,
    )


@router.get(
    "/delivery-events",
    response_model=ListDeliveryEventsResponseSchema,
)
async def list_delivery_events(
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryEventsUseCaseDep,
    outbound_message_id: UUID | None = None,
    external_message_id: str | None = None,
    internal_status: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ListDeliveryEventsResponseSchema:
    """HTTP controller списка delivery events."""
    return await _list_delivery_events(
        context=context,
        use_case=use_case,
        limit=limit,
        offset=offset,
        outbound_message_id=outbound_message_id,
        external_message_id=external_message_id,
        internal_status=internal_status,
        event_type=event_type,
    )


async def _list_delivery_events(
    *,
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryEventsUseCaseDep,
    limit: int,
    offset: int,
    outbound_message_id: UUID | None,
    external_message_id: str | None,
    internal_status: str | None,
    event_type: str | None,
) -> ListDeliveryEventsResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        items = await use_case(
            ListDeliveryEventsQuery(
                tenant_id=EntityIdVO.from_value(tenant_id),
                limit=limit,
                offset=offset,
                outbound_message_id=(
                    None
                    if outbound_message_id is None
                    else OutboundMessageIdVO.from_value(outbound_message_id)
                ),
                external_message_id=external_message_id,
                internal_status=internal_status,
                event_type=event_type,
            )
        )
    except Exception as exc:
        raise map_communication_http_error(exc) from exc
    return ListDeliveryEventsResponseSchema(
        items=[
            DeliveryEventResponseSchema(
                delivery_event_id=item.delivery_event_id,
                tenant_id=item.tenant_id,
                outbound_message_id=item.outbound_message_id,
                provider_connection_id=item.provider_connection_id,
                external_message_id=item.external_message_id,
                external_status=item.external_status,
                internal_status=item.internal_status,
                event_type=item.event_type,
                event_at=item.event_at,
                raw_payload=dict(item.raw_payload),
                created_at=item.created_at,
            )
            for item in items
        ]
    )


__all__ = [
    "list_delivery_events",
    "list_message_delivery_events",
    "router",
]
