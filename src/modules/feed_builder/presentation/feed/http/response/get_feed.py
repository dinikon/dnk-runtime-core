from datetime import datetime
from uuid import UUID
from typing import Self
from pydantic import BaseModel, ConfigDict, Field
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.presentation.feed.http.schema.export_settings import (
    FeedExportSettingsSchema,
)


class GetFeedResponse(BaseModel):
    """Передаёт результат чтения карточки Feed через собственную HTTP-схему."""

    model_config = ConfigDict(populate_by_name=True)
    id: UUID
    name: str
    code: str
    status: str
    export_settings: FeedExportSettingsSchema
    schema_definition: JsonObject = Field(alias="schema")
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, value: FeedDetailsDTO) -> Self:
        """Явно преобразует DTO данного сценария в HTTP-ответ."""
        return cls(
            id=value.id,
            name=value.name,
            code=value.code,
            status=value.status,
            export_settings=FeedExportSettingsSchema.from_dto(value.export_settings),
            schema_definition=value.schema,
            version=value.version,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )
