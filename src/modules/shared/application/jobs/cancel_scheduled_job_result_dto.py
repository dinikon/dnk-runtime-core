from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CancelScheduledJobResultDTO:
    """Result of canceling one scheduled job."""

    canceled: bool


__all__ = ["CancelScheduledJobResultDTO"]
