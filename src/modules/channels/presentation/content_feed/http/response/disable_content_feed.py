from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.command.disable_content_feed.dto import (
    DisableContentFeedResultDTO,
)


class DisableContentFeedResponse(BaseModel):
    """Ответ отдельного HTTP-сценария disable_content_feed."""

    feed: FeedFields

    @classmethod
    def from_dto(
        cls, value: DisableContentFeedResultDTO
    ) -> "DisableContentFeedResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
