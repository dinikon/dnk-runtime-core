from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CancelScheduledJobCommand:
    """Command for canceling one scheduled job."""

    job_id: UUID


__all__ = ["CancelScheduledJobCommand"]
