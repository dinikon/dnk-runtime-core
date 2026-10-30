from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.content_feed.query.preview_content_feed.dto import (
    PreviewContentFeedResultDTO,
)


class FeedStatisticsResponse(BaseModel):
    """Счётчики полностью проверенного XML."""

    offers: int
    changed_offers: int
    categories: int


class FeedPreviewIssueResponse(BaseModel):
    """Безопасная ошибка позиции или всего фида."""

    code: str
    publication_id: UUID | None
    field: str | None


class PreviewContentFeedResponse(BaseModel):
    """Результат диагностической сборки без публикации ссылки."""

    ready: bool
    statistics: FeedStatisticsResponse | None
    issues: list[FeedPreviewIssueResponse]

    @classmethod
    def from_dto(
        cls, value: PreviewContentFeedResultDTO
    ) -> "PreviewContentFeedResponse":
        """Переносит только безопасные поля диагностики."""
        return cls(
            ready=value.ready,
            statistics=(
                FeedStatisticsResponse(
                    offers=value.statistics.offers,
                    changed_offers=value.statistics.changed_offers,
                    categories=value.statistics.categories,
                )
                if value.statistics
                else None
            ),
            issues=[
                FeedPreviewIssueResponse(
                    code=v.code, publication_id=v.publication_id, field=v.field
                )
                for v in value.issues
            ],
        )
