from enum import StrEnum


class AccessKeyStatus(StrEnum):
    """Определяет действительность отдельного ключа публичной выгрузки."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
