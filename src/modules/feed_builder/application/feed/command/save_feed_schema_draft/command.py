from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.application.feed.types import JsonObject


@dataclass(frozen=True, slots=True)
class SaveFeedSchemaDraftCommand:
    """Передаёт полный документ рабочей схемы и общую ожидаемую версию Feed."""

    feed_id: FeedIdVO
    expected_version: int
    definition: JsonObject
