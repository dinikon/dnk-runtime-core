from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.dto import (
    FeedAccessKeyViewStatus,
)


class FeedAccessKeyItemResponse(BaseModel):
    """Отображает срок и состояние ключа для управления в Console."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: FeedAccessKeyViewStatus
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


class ListFeedAccessKeysResponse(BaseModel):
    """Содержит только метаданные ключей."""

    model_config = ConfigDict(from_attributes=True)
    items: tuple[FeedAccessKeyItemResponse, ...]
