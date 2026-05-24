from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.shared.domain.jobs.scheduled_job_status import ScheduledJobStatus


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    """Shared scheduled job contract for deferred/timer/polling work."""

    id: UUID
    tenant_id: UUID
    job_type: str
    payload: dict[str, Any]
    run_at: datetime
    status: str
    attempts: int
    locked_until: datetime | None
    lock_token: str | None
    created_at: datetime
    updated_at: datetime
    last_error: str | None = None

    @property
    def status_enum(self) -> ScheduledJobStatus:
        """Returns typed status enum for transition checks."""
        return ScheduledJobStatus(self.status)

    def is_terminal(self) -> bool:
        """Returns True when the job should not be mutated by worker commands."""
        return self.status_enum.is_terminal()

    def to_payload(self) -> dict[str, Any]:
        """Serializes the job into a database/API friendly payload."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "job_type": self.job_type,
            "payload": dict(self.payload),
            "run_at": self.run_at.isoformat(),
            "status": self.status,
            "attempts": self.attempts,
            "locked_until": (
                self.locked_until.isoformat() if self.locked_until else None
            ),
            "lock_token": self.lock_token,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_error": self.last_error,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ScheduledJob":
        """Builds a scheduled job from a serialized payload."""
        job_payload = payload.get("payload") or {}
        if not isinstance(job_payload, Mapping):
            raise TypeError("Scheduled job payload must be a mapping.")
        locked_until = payload.get("locked_until")
        return cls(
            id=UUID(str(payload["id"])),
            tenant_id=UUID(str(payload["tenant_id"])),
            job_type=str(payload["job_type"]),
            payload=dict(job_payload),
            run_at=datetime.fromisoformat(str(payload["run_at"])),
            status=str(payload["status"]),
            attempts=int(payload["attempts"]),
            locked_until=(
                datetime.fromisoformat(str(locked_until)) if locked_until else None
            ),
            lock_token=(
                str(payload["lock_token"]) if payload.get("lock_token") else None
            ),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            last_error=(
                str(payload["last_error"]) if payload.get("last_error") else None
            ),
        )


__all__ = ["ScheduledJob"]
