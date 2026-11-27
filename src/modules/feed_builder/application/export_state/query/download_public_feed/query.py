from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.access_key.value_object.access_token_hash import (
    AccessTokenHashVO,
)


@dataclass(frozen=True, slots=True)
class DownloadPublicFeedQuery:
    """Передаёт хост запроса, публичную ссылку и запрошенный формат."""

    host: str
    public_link_id: UUID
    format: ExportFormat
    token_hash: AccessTokenHashVO | None = None
