from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat


@dataclass(frozen=True, slots=True)
class DownloadPublicFeedQuery:
    """Передаёт параметры доверенного tenant-запроса."""

    public_link_id: UUID
    format: ExportFormat
