from dataclasses import dataclass
from src.modules.channels.application.content_feed.contracts import RenderedFeed


@dataclass(frozen=True, slots=True)
class GetContentFeedXmlResultDTO:
    """Явный результат сценария get_content_feed_xml."""

    document: RenderedFeed
