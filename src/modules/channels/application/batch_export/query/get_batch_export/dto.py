from dataclasses import dataclass, field
from datetime import datetime
from src.modules.channels.application.batch_export.contracts import (
    BatchExportSummaryDTO,
    BatchExportItemDTO,
)


@dataclass(frozen=True, slots=True)
class BatchExportDetailDTO:
    """Передаёт ограниченную страницу истории с общим числом позиций."""

    run: BatchExportSummaryDTO
    items: tuple[BatchExportItemDTO, ...]
    total: int
    feed_url: str | None = field(default=None, repr=False)
    feed_expires_at: datetime | None = None
