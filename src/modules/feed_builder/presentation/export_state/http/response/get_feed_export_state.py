from datetime import datetime

from pydantic import BaseModel

from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy
from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode


class ExportTaskResponse(BaseModel):
    """Передаёт статус текущей пересборки."""

    status: str
    requested_at: datetime
    started_at: datetime | None


class ExportReportResponse(BaseModel):
    """Передаёт итог последней проверки."""

    completed_at: datetime
    as_of: datetime | None
    validation_policy: ValidationPolicy
    outcome: str
    reason_code: str | None
    is_complete: bool
    total_items: int
    valid_items: int
    warning_items: int
    rejected_items: int


class ActiveFileResponse(BaseModel):
    """Передаёт публичный адрес текущего файла."""

    url: str
    format: str
    as_of: datetime
    published_at: datetime


class GetFeedExportStateResponse(BaseModel):
    """Передаёт текущую задачу, последний отчёт и доступный файл."""

    feed_version: int
    can_refresh: bool
    can_rotate: bool
    access_mode: FeedAccessMode
    can_manage_access: bool
    task: ExportTaskResponse | None
    report: ExportReportResponse | None
    active: ActiveFileResponse | None
