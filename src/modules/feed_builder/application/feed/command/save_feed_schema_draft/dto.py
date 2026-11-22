from dataclasses import dataclass
from uuid import UUID
from src.modules.feed_builder.application.feed.types import JsonObject


@dataclass(frozen=True, slots=True)
class SaveFeedSchemaDraftResultDTO:
    """Возвращает подтверждённый снимок и версию агрегата без ревизий схемы."""

    feed_id: UUID
    version: int
    definition: JsonObject
