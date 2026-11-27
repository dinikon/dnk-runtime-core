from dataclasses import dataclass
from datetime import datetime

from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class IssueFeedAccessKeyCommand:
    """Передаёт фид и настройки выпуска одного ключа."""

    feed_id: FeedIdVO
    name: str
    expires_at: datetime | None
