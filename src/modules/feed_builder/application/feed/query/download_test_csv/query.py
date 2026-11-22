from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class DownloadTestCsvQuery:
    """Запрашивает пробный CSV сохранённой версии Feed."""

    feed_id: FeedIdVO
    expected_version: int
