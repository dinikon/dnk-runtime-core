from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContentFeedXmlQuery:
    """Вход отдельного сценария get_content_feed_xml."""

    feed_id: UUID
    token: str = field(repr=False)
