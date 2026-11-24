from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListLatestFeedExportIssuesQuery:
    """Передаёт параметры доверенного tenant-запроса."""

    feed_id: UUID
    severity: str | None
    limit: int
    offset: int
