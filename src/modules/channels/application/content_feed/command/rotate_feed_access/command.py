from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RotateFeedAccessCommand:
    """Намерение выполнить отдельный сценарий rotate_feed_access."""

    channel_id: UUID
    feed_id: UUID
    expected_revision: int
    actor_id: UUID
