from enum import StrEnum


class ExportTaskStatus(StrEnum):
    """Состояние незавершённой пересборки."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
