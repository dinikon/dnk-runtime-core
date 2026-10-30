from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class RevokeFeedAccessResultDTO:
    """Публичный результат сценария revoke_feed_access."""

    feed: FeedDetails
