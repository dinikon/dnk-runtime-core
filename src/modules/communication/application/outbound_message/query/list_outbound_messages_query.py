from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListOutboundMessagesQuery:
    """Query списка outbound messages tenant."""

    tenant_id: EntityIdVO
    limit: int
    offset: int


__all__ = ["ListOutboundMessagesQuery"]
