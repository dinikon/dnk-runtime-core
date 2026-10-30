from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.command.enable_content_feed.dto import (
    EnableContentFeedResultDTO,
)


class EnableContentFeedResponse(BaseModel):
    """Ответ отдельного HTTP-сценария enable_content_feed."""

    feed: FeedFields

    @classmethod
    def from_dto(cls, value: EnableContentFeedResultDTO) -> "EnableContentFeedResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
