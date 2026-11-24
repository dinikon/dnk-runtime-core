from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetFeedExportStateQuery:
    """Передаёт параметры доверенного tenant-запроса."""

    feed_id: UUID
