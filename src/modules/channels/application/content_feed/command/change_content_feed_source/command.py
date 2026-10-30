from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO


@dataclass(frozen=True, slots=True)
class ChangeContentFeedSourceCommand:
    """Намерение выполнить отдельный сценарий change_content_feed_source."""

    channel_id: UUID
    feed_id: UUID
    expected_revision: int
    actor_id: UUID
    source: FeedSourceVO
    source_url: str | None = field(repr=False)
