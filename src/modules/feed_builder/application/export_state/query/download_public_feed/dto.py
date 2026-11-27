from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode


@dataclass(frozen=True, slots=True)
class DownloadPublicFeedResultDTO:
    """Содержит разрешённый файл и tenant для открытия потока."""

    tenant_id: UUID
    file_id: UUID
    published_at: datetime
    access_mode: FeedAccessMode
