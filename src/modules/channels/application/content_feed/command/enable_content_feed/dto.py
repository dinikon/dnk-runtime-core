from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class EnableContentFeedResultDTO:
    """Публичный результат сценария enable_content_feed."""

    feed: FeedDetails
