from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.domain.jobs import ScheduledJobStatus
from src.modules.shared.infrastructure.persistence import (
    Base,
    LongText,
    PortableJSON,
    StringUUID,
)


class ScheduledJobModel(Base):
    """Global PostgreSQL storage for shared scheduled jobs."""

    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        Index("scheduled_jobs_due_idx", "status", "run_at"),
        Index("scheduled_jobs_stuck_idx", "status", "locked_until"),
        Index("scheduled_jobs_tenant_type_idx", "tenant_id", "job_type"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True, nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=sa.text(f"'{ScheduledJobStatus.SCHEDULED.value}'"),
        default=ScheduledJobStatus.SCHEDULED.value,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=sa.text("0"),
        default=0,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    lock_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(LongText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


__all__ = ["ScheduledJobModel"]
