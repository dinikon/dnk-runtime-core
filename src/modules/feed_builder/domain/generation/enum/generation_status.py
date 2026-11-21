from enum import StrEnum


class GenerationStatus(StrEnum):
    """Определяет состояние сборки отдельно от активации её результата."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
