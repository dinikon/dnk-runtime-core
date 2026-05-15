from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProcessOutboundMessageResultDTO:
    """DTO результата обработки одного outbound message."""

    outbound_message_id: UUID
    processed: bool
    succeeded: bool
    skipped: bool
    status: str
    error_message: str | None = None


__all__ = ["ProcessOutboundMessageResultDTO"]
