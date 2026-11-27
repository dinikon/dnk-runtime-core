from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class ChangeFeedAccessModeCommand:
    """Передаёт новый режим и ожидаемую версию фида."""

    feed_id: FeedIdVO
    expected_version: int
    access_mode: FeedAccessMode
