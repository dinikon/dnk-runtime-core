from pydantic import BaseModel
from src.modules.channels.presentation.content_feed.http.response.fields import (
    FeedFields,
)
from src.modules.channels.application.content_feed.query.list_content_feeds.dto import (
    ListContentFeedsResultDTO,
)


class ListContentFeedsResponse(BaseModel):
    """Ответ отдельного HTTP-сценария list_content_feeds."""

    items: list[FeedFields]

    @classmethod
    def from_dto(cls, value: ListContentFeedsResultDTO) -> "ListContentFeedsResponse":
        """Явно переносит публичную проекцию."""
        return cls(items=[FeedFields.from_details(item) for item in value.items])
