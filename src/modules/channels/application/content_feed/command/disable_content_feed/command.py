from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DisableContentFeedCommand:
    """Намерение выполнить отдельный сценарий disable_content_feed."""

    channel_id: UUID
    feed_id: UUID
    expected_revision: int
    actor_id: UUID
