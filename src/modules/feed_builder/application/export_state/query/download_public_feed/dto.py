from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DownloadPublicFeedResultDTO:
    """Содержит разрешённый файл и tenant для открытия потока."""

    tenant_id: UUID
    file_id: UUID
    published_at: datetime
