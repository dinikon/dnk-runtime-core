from enum import StrEnum


class LocaleFallbackMode(StrEnum):
    """Задаёт явное поведение при отсутствии перевода."""

    NONE = "NONE"
    LOCALE_CHAIN = "LOCALE_CHAIN"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
