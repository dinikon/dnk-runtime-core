from src.modules.shared.domain.errors import DomainError


class InvalidOtpChallengeError(DomainError):
    """Ошибка отсутствующего или истекшего OTP challenge."""

    def __init__(self):
        """Формирует сообщение о невалидном OTP challenge."""
        super().__init__("OTP challenge is invalid or expired.")


class InvalidOtpCodeError(DomainError):
    """Ошибка неверного OTP code."""

    def __init__(self):
        """Формирует сообщение о неверном OTP code."""
        super().__init__("OTP code is invalid.")


class InvalidSessionError(DomainError):
    """Ошибка невалидной или истекшей session."""

    def __init__(self):
        """Формирует сообщение о невалидной session."""
        super().__init__("Session is invalid or expired.")


__all__ = [
    "InvalidOtpChallengeError",
    "InvalidOtpCodeError",
    "InvalidSessionError",
]
