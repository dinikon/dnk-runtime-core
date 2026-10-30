from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class DisableContentFeedResultDTO:
    """Публичный результат сценария disable_content_feed."""

    feed: FeedDetails
