from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class PreviewFeedQuery:
    """Запрашивает образец включённых публикаций сохранённой схемы."""

    feed_id: FeedIdVO
    expected_version: int
