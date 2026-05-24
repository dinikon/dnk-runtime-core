from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecoverStuckJobsResultDTO:
    """Result of one stuck scheduled jobs recovery batch."""

    scanned: int
    recovered: int
    failed: int


__all__ = ["RecoverStuckJobsResultDTO"]
