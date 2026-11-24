from enum import StrEnum


class ExportOutcome(StrEnum):
    """Итог последней проверки экспорта."""

    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
