from enum import StrEnum


class PublicationStatus(StrEnum):
    """Определяет участие выбранной позиции в выгрузке отдельно от готовности."""

    DRAFT = "DRAFT"
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"
