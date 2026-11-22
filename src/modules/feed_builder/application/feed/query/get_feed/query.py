from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class GetFeedQuery:
    """Запрашивает карточку, включая сохранённую архивную запись."""

    feed_id: FeedIdVO
