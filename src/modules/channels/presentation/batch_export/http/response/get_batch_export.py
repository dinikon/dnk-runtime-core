from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from src.modules.channels.presentation.batch_export.http.response.contracts import (
    BatchExportSummaryResponse,
)


class BatchExportItemResponse(BaseModel):
    """Возвращает результат позиции без приватных метаданных."""

    publication_id: UUID
    catalog_item_id: UUID
    external_id: str
    status: str
    issues: list[str]
    titles: dict[str, str]


class GetBatchExportResponse(BaseModel):
    """Описывает страницу результатов одного пакета."""

    run: BatchExportSummaryResponse
    items: list[BatchExportItemResponse]
    total: int
    feed_url: str | None
    feed_expires_at: datetime | None
