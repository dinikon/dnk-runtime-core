from pydantic import BaseModel, ConfigDict

from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode


class ChangeFeedAccessModeResponse(BaseModel):
    """Возвращает сохранённый режим скачивания."""

    model_config = ConfigDict(from_attributes=True)
    access_mode: FeedAccessMode
    feed_version: int
