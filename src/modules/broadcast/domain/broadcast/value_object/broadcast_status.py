from enum import StrEnum


class BroadcastStatus(StrEnum):
    DRAFT = "DRAFT"
    PREPARING = "preparing"
    READY = "ready"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
