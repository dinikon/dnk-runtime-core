from enum import StrEnum


class ContentValueType(StrEnum):
    """Поддержанные первым срезом типы содержимого."""

    TEXT = "text"
    RICH_TEXT = "rich_text"
