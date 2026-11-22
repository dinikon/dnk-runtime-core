from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class GetFeedSchemaQuery:
    """Запрашивает единственную рабочую схему текущего Feed."""

    feed_id: FeedIdVO
