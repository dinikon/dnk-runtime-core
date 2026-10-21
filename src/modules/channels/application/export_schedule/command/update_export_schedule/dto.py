from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UpdateExportScheduleResultDTO:
    """Возвращает зафиксированную версию и ближайший запуск."""

    revision: int
    next_at: datetime | None
