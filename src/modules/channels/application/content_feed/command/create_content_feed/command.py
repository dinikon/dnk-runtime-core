from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO


@dataclass(frozen=True, slots=True)
class CreateContentFeedCommand:
    """Намерение выполнить отдельный сценарий create_content_feed."""

    channel_id: UUID
    actor_id: UUID
    source: FeedSourceVO
    source_url: str = field(repr=False)
