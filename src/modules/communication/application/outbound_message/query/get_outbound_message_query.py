from dataclasses import dataclass

from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetOutboundMessageQuery:
    """Query получения outbound message по id."""

    tenant_id: EntityIdVO
    outbound_message_id: OutboundMessageIdVO


__all__ = ["GetOutboundMessageQuery"]
