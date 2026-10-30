from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.application.content_feed.contracts import FeedDetails


class FeedFields(BaseModel):
    """Общие вложенные публичные поля карточки без persistence-секретов."""

    id: UUID
    revision: int
    enabled: bool
    scope_key: str
    source_schema: str
    source_settings: JsonObject
    public_url: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_details(cls, value: FeedDetails) -> "FeedFields":
        """Явно переносит разрешённые поля в HTTP-схему."""
        return cls(
            id=value.id,
            revision=value.revision,
            enabled=value.enabled,
            scope_key=value.scope_key,
            source_schema=value.source_schema,
            source_settings=value.source_settings,
            public_url=value.public_url,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )
