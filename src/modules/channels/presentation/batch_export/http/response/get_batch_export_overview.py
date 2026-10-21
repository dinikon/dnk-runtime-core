from pydantic import BaseModel
from src.modules.channels.presentation.batch_export.http.response.contracts import (
    BatchExportSummaryResponse,
    ExportScheduleResponse,
)


class GetBatchExportOverviewResponse(BaseModel):
    """Описывает отдельный HTTP контракт настроек, состава и истории."""

    outbound_enabled: bool
    delivery_configured: bool
    feed_available: bool
    bound_count: int
    enabled_count: int
    schedule: ExportScheduleResponse
    recent: list[BatchExportSummaryResponse]
