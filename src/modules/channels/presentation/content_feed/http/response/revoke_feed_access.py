from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.command.revoke_feed_access.dto import (
    RevokeFeedAccessResultDTO,
)


class RevokeFeedAccessResponse(BaseModel):
    """Ответ отдельного HTTP-сценария revoke_feed_access."""

    feed: FeedFields

    @classmethod
    def from_dto(cls, value: RevokeFeedAccessResultDTO) -> "RevokeFeedAccessResponse":
        """Явно переносит публичную проекцию."""
        return cls(feed=FeedFields.from_details(value.feed))
