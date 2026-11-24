from dataclasses import dataclass
from datetime import datetime

from src.modules.feed_builder.domain.export_state.enum.export_task_status import (
    ExportTaskStatus,
)


@dataclass(frozen=True, slots=True)
class RequestFeedRefreshResultDTO:
    """Передаёт состояние принятой задачи."""

    status: ExportTaskStatus
    requested_at: datetime
