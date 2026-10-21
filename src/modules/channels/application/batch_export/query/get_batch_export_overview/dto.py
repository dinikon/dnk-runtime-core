from dataclasses import dataclass
from datetime import datetime
from src.modules.channels.application.batch_export.contracts import (
    BatchExportSummaryDTO,
)


@dataclass(frozen=True, slots=True)
class ExportScheduleDTO:
    """Показывает календарную policy и её версию."""

    enabled: bool
    hour: int
    minute: int
    timezone: str
    revision: int
    next_at: datetime | None


@dataclass(frozen=True, slots=True)
class GetBatchExportOverviewResultDTO:
    """Показывает готовность пакетного сценария без выполнения сети."""

    outbound_enabled: bool
    delivery_configured: bool
    bound_count: int
    enabled_count: int
    schedule: ExportScheduleDTO
    recent: tuple[BatchExportSummaryDTO, ...]
    feed_available: bool
