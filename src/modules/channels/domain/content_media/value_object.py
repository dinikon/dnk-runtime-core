from enum import StrEnum


class MediaTransferStatus(StrEnum):
    """Отделяет доступность URL от подтверждённого внешнего attachment."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    READY = "ready"
    UNKNOWN = "unknown"
    FAILED = "failed"
