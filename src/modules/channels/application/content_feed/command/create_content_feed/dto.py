from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class CreateContentFeedResultDTO:
    """Публичный результат сценария create_content_feed."""

    feed: FeedDetails
