from dataclasses import dataclass
from uuid import UUID
from src.modules.feed_builder.application.feed.types import JsonObject


@dataclass(frozen=True, slots=True)
class FeedSchemaDetailsDTO:
    """Передаёт рабочее определение, общую версию и режим просмотра архива."""

    feed_id: UUID
    version: int
    status: str
    definition: JsonObject
