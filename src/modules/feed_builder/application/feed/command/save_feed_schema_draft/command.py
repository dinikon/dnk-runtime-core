from dataclasses import dataclass
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class SaveFeedSchemaDraftCommand:
    """Запрашивает сохранение графа версии 2 с ожидаемой версией Feed."""

    feed_id: FeedIdVO
    expected_version: int
    definition: JsonObject
