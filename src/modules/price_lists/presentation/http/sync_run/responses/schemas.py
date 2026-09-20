from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Any
from pydantic import BaseModel


class SyncRunResponse(BaseModel):
    """HTTP-представление SyncRunResponse."""

    id: UUID
    price_list_id: UUID
    scheduled_job_id: UUID | None
    status: str
    trigger: str
    planned_at: datetime | None
    started_at: datetime
    finished_at: datetime | None
    source_checksum: str | None
    counters: dict[str, int]
    error_summary: str | None


__all__ = ["SyncRunResponse"]
