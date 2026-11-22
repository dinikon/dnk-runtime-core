from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.dto import (
    SaveFeedSchemaDraftResultDTO,
)
from src.modules.feed_builder.presentation.feed.http.schema.definition import (
    SchemaDefinition,
)


class PutFeedSchemaResponse(BaseModel):
    """Возвращает собственный HTTP-контракт сценария рабочей схемы."""

    feed_id: UUID
    version: int
    definition: SchemaDefinition

    @classmethod
    def from_dto(cls, value: SaveFeedSchemaDraftResultDTO) -> Self:
        """Явно преобразует результат без передачи Application DTO в ответ."""
        return cls(
            feed_id=value.feed_id,
            version=value.version,
            definition=SchemaDefinition.model_validate(value.definition),
        )
