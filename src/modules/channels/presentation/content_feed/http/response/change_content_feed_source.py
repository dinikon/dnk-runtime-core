from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.command.change_content_feed_source.dto import (
    ChangeContentFeedSourceResultDTO,
)


class ChangeContentFeedSourceResponse(BaseModel):
    """Ответ отдельного HTTP-сценария change_content_feed_source."""

    feed: FeedFields

    @classmethod
    def from_dto(
        cls, value: ChangeContentFeedSourceResultDTO
    ) -> "ChangeContentFeedSourceResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
