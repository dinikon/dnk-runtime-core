"""Состояния проверки доступа к магазину."""

from enum import StrEnum


class VerificationStatus(StrEnum):
    """Перечисляет состояния; переходами управляет подключение."""

    PENDING = "pending"
    VERIFIED = "verified"
    ERROR = "error"
