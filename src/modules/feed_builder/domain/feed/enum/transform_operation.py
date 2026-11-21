from enum import StrEnum


class TransformOperation(StrEnum):
    """Перечисляет поддержанные определения преобразований."""

    STRING_TRIM = "string.trim"
    STRING_TRUNCATE = "string.truncate"
    MONEY_CEIL_STEP = "money.ceil_step"
