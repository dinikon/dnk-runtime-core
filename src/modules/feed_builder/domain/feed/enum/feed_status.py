from enum import StrEnum


class FeedStatus(StrEnum):
    """Перечисляет состояния Feed без реализации переходов."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"
