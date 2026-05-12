from __future__ import annotations

from enum import StrEnum


class AttemptStatus(StrEnum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    RETRYABLE_FAILED = "RETRYABLE_FAILED"
    NON_RETRYABLE_FAILED = "NON_RETRYABLE_FAILED"
    TIMEOUT = "TIMEOUT"


class DeliveryEventType(StrEnum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"


__all__ = [
    "AttemptStatus",
    "DeliveryEventType",
]

