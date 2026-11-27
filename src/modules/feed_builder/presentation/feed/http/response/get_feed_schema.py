from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.feed_builder.application.feed.query.get_feed_schema.dto import (
    FeedSchemaDetailsDTO,
)
from src.modules.feed_builder.presentation.feed.http.schema.graph import (
    FieldGraphSchema,
)


class GetFeedSchemaResponse(BaseModel):
    """Возвращает собственный HTTP-контракт сценария рабочей схемы."""

    feed_id: UUID
    version: int
    status: str
    definition: FieldGraphSchema

    @classmethod
    def from_dto(cls, value: FeedSchemaDetailsDTO) -> Self:
        """Явно преобразует результат без передачи Application DTO в ответ."""
        return cls(
            feed_id=value.feed_id,
            version=value.version,
            status=value.status,
            definition=FieldGraphSchema.model_validate(value.definition),
        )
