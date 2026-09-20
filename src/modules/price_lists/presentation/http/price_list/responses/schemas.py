from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel


class PriceListResponse(BaseModel):
    """HTTP-представление PriceListResponse."""

    id: UUID
    title: str
    status: str
    source_format: str
    source_preset: str | None
    source_url_display: str
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]
    mapping_version: int
    cron_expression: str | None
    timezone: str
    new_item_policy: str
    missing_item_policy: str
    missing_threshold: int
    schedule_revision: int
    created_at: datetime
    updated_at: datetime
    next_sync_at: datetime | None
    last_sync_run_id: UUID | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    archived_at: datetime | None


class PriceListListItemResponse(PriceListResponse):
    """HTTP-представление PriceListListItemResponse."""

    active_offer_count: int
    last_run_status: str | None


class ActionResponse(BaseModel):
    """HTTP-представление ActionResponse."""

    id: UUID | None = None
    status: str | None = None
    job_id: UUID | None = None
    canceled_jobs: int | None = None
    next_sync_at: datetime | None = None


class PreviewRowResponse(BaseModel):
    """HTTP-представление PreviewRowResponse."""

    row_number: int
    values: dict[str, Any]
    errors: tuple[str, ...]


class PreviewResponse(BaseModel):
    """HTTP-представление PreviewResponse."""

    format: str
    content_type: str
    size: int
    checksum: str
    rows: tuple[PreviewRowResponse, ...]
    sheets: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()


class SchedulePreviewResponse(BaseModel):
    """HTTP-представление SchedulePreviewResponse."""

    occurrences: tuple[datetime, ...]


__all__ = [
    "PriceListResponse",
    "PriceListListItemResponse",
    "ActionResponse",
    "PreviewRowResponse",
    "PreviewResponse",
    "SchedulePreviewResponse",
]
