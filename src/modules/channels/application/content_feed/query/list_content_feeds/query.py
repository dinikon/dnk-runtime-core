from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListContentFeedsQuery:
    """Вход отдельного сценария list_content_feeds."""

    channel_id: UUID
