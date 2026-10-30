from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class RotateFeedAccessResultDTO:
    """Публичный результат сценария rotate_feed_access."""

    feed: FeedDetails
