from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ScheduleScheduledJobCommand:
    """Command for scheduling a shared deferred job."""

    tenant_id: UUID
    job_type: str
    payload: dict[str, Any]
    run_at: datetime
    job_id: UUID | None = None


__all__ = ["ScheduleScheduledJobCommand"]
