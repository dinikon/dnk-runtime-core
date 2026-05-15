from __future__ import annotations

from enum import StrEnum


class RequestStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class OutboundMessageStatus(StrEnum):
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    UNDELIVERED = "UNDELIVERED"
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"


__all__ = [
    "OutboundMessageStatus",
    "RequestStatus",
]
