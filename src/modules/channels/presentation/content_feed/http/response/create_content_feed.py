from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.command.create_content_feed.dto import (
    CreateContentFeedResultDTO,
)


class CreateContentFeedResponse(BaseModel):
    """Ответ отдельного HTTP-сценария create_content_feed."""

    feed: FeedFields

    @classmethod
    def from_dto(cls, value: CreateContentFeedResultDTO) -> "CreateContentFeedResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
