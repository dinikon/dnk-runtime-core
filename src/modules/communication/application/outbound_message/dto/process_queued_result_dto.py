from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessQueuedResultDTO:
    """DTO результата batch processing queued messages."""

    processed: int
    succeeded: int
    failed: int


__all__ = ["ProcessQueuedResultDTO"]
