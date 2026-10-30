from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContentFeedQuery:
    """Вход отдельного сценария get_content_feed."""

    channel_id: UUID
    feed_id: UUID
