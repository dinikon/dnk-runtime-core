from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EnableContentFeedCommand:
    """Намерение выполнить отдельный сценарий enable_content_feed."""

    channel_id: UUID
    feed_id: UUID
    expected_revision: int
    actor_id: UUID
