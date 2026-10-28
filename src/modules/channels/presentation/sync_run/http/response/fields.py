"""Публичные поля состояния запуска без checkpoint и current_job_id."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.channels.application.sync_run.port.query_repository import (
    SyncRunReadRow,
)


class SyncRunFields(BaseModel):
    """Компонент ответов конкретных сценариев чтения."""

    id: UUID
    config_revision: int
    revision: int
    status: str
    processed_count: int
    skipped_count: int
    pages_count: int
    automatic: bool
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    recovery_required: bool

    @classmethod
    def from_row(cls, row: SyncRunReadRow) -> "SyncRunFields":
        """Явно выбирает публичные поля read-side."""
        return cls(
            id=row.id,
            config_revision=row.config_revision,
            revision=row.revision,
            status=row.status,
            processed_count=row.processed_count,
            skipped_count=row.skipped_count,
            pages_count=row.pages_count,
            automatic=row.automatic,
            error_code=row.error_code,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            recovery_required=row.recovery_required,
        )
