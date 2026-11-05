from enum import StrEnum


class CountSheetStatus(StrEnum):
    """Разделяет ввод, передачу, отзыв и отмену ведомости без применения к запасам."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"
