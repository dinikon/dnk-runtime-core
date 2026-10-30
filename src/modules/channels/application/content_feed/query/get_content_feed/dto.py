from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class GetContentFeedResultDTO:
    """Явный результат сценария get_content_feed."""

    feed: FeedDetails
