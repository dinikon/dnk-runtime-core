from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode


@dataclass(frozen=True, slots=True)
class ChangedFeedAccessModeDTO:
    """Подтверждает режим и актуальную версию фида."""

    access_mode: FeedAccessMode
    feed_version: int
