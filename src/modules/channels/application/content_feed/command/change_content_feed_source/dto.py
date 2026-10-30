from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class ChangeContentFeedSourceResultDTO:
    """Публичный результат сценария change_content_feed_source."""

    feed: FeedDetails
