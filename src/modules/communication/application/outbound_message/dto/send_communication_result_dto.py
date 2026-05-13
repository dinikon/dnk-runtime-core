from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SendCommunicationResultDTO:
    """DTO результата постановки communication send."""

    communication_request_id: UUID
    outbound_message_id: UUID
    status: str
    internal_status: str
    idempotent: bool


__all__ = ["SendCommunicationResultDTO"]
