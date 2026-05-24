from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared.domain.jobs import ScheduledJob


@dataclass(frozen=True, slots=True)
class ScheduleScheduledJobResultDTO:
    """Result of scheduling one shared job."""

    job: ScheduledJob


__all__ = ["ScheduleScheduledJobResultDTO"]
