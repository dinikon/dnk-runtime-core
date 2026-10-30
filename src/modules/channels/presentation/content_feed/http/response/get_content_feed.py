from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.query.get_content_feed.dto import (
    GetContentFeedResultDTO,
)


class GetContentFeedResponse(BaseModel):
    """Ответ отдельного HTTP-сценария get_content_feed."""

    feed: FeedFields

    @classmethod
    def from_dto(cls, value: GetContentFeedResultDTO) -> "GetContentFeedResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
