from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.content_feed.contracts import FeedStatistics


@dataclass(frozen=True, slots=True)
class FeedPreviewIssue:
    """Безопасная причина отказа всего документа или выбранной публикации."""

    code: str
    publication_id: UUID | None
    field: str | None


@dataclass(frozen=True, slots=True)
class PreviewContentFeedResultDTO:
    """Диагностика полного фида без URL источника или XML в JSON."""

    ready: bool
    statistics: FeedStatistics | None
    issues: tuple[FeedPreviewIssue, ...]
