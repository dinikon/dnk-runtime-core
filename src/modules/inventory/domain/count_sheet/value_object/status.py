from enum import StrEnum


class CountSheetStatus(StrEnum):
    """Разделяет ввод результатов, передачу ведомости и отмену без применения к запасам."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CANCELLED = "CANCELLED"
