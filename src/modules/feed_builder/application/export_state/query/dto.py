from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO
from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode


@dataclass(frozen=True, slots=True)
class FeedExportTaskDTO:
    """Описание выполняющейся задачи без внутреннего снимка."""

    status: str
    requested_at: datetime
    started_at: datetime | None


@dataclass(frozen=True, slots=True)
class FeedExportReportDTO:
    """Сводка последней завершённой проверки."""

    completed_at: datetime
    as_of: datetime | None
    validation_policy: str
    outcome: str
    reason_code: str | None
    is_complete: bool
    total_items: int
    valid_items: int
    warning_items: int
    rejected_items: int


@dataclass(frozen=True, slots=True)
class ActiveFeedFileDTO:
    """Описание текущей публичной выдачи."""

    public_link_id: UUID
    format: str
    as_of: datetime
    published_at: datetime


@dataclass(frozen=True, slots=True)
class FeedExportStateDTO:
    """Проекция состояния экспорта выбранного Feed."""

    feed_version: int
    can_refresh: bool
    can_rotate: bool
    task: FeedExportTaskDTO | None
    report: FeedExportReportDTO | None
    active: ActiveFeedFileDTO | None
    access_mode: FeedAccessMode
    can_manage_access: bool


@dataclass(frozen=True, slots=True)
class FeedExportIssuesPageDTO:
    """Страница диагностик единственного актуального отчёта."""

    items: tuple[FeedExportIssueDTO, ...]
    total: int


@dataclass(frozen=True, slots=True)
class PublicFeedFileDTO:
    """Метаданные активной ссылки для HTTP-выдачи."""

    file_id: UUID
    published_at: datetime
    access_mode: FeedAccessMode
