from enum import StrEnum


class BroadcastStatusVO(StrEnum):
    DRAFT = "DRAFT"
    PREPARED = "PREPARED"

    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
