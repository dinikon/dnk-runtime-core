from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import FeedDetails


@dataclass(frozen=True, slots=True)
class ListContentFeedsResultDTO:
    """Явный результат сценария list_content_feeds."""

    items: tuple[FeedDetails, ...]
