from dataclasses import dataclass

from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListDeliveryAttemptsQuery:
    """Query списка delivery attempts tenant."""

    tenant_id: EntityIdVO
    limit: int
    offset: int
    outbound_message_id: OutboundMessageIdVO | None = None
    status: str | None = None


__all__ = ["ListDeliveryAttemptsQuery"]
