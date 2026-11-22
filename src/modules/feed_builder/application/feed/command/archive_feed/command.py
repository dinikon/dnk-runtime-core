from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class ArchiveFeedCommand:
    """Передаёт намерение архивировать фид без физического удаления."""

    feed_id: FeedIdVO
    expected_version: int
