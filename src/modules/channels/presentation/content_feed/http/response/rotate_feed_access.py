from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.command.rotate_feed_access.dto import (
    RotateFeedAccessResultDTO,
)


class RotateFeedAccessResponse(BaseModel):
    """Ответ отдельного HTTP-сценария rotate_feed_access."""

    feed: FeedFields

    @classmethod
    def from_dto(cls, value: RotateFeedAccessResultDTO) -> "RotateFeedAccessResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
