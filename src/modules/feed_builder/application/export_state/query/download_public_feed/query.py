from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat


@dataclass(frozen=True, slots=True)
class DownloadPublicFeedQuery:
    """Передаёт хост запроса, публичную ссылку и запрошенный формат."""

    host: str
    public_link_id: UUID
    format: ExportFormat
