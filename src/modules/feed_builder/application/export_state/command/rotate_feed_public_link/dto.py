from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat


@dataclass(frozen=True, slots=True)
class RotateFeedPublicLinkResultDTO:
    """Передаёт новый идентификатор и формат текущего файла."""

    public_link_id: UUID
    format: ExportFormat
    feed_version: int
