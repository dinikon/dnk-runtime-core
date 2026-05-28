from dataclasses import dataclass

from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListDeliveryEventsQuery:
    """Query списка delivery events tenant."""

    tenant_id: EntityIdVO
    limit: int
    offset: int
    outbound_message_id: OutboundMessageIdVO | None = None
    external_message_id: str | None = None
    internal_status: str | None = None
    event_type: str | None = None


__all__ = ["ListDeliveryEventsQuery"]
