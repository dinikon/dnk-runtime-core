from src.modules.shared.domain.errors import DomainError


class UserEmailAlreadyExistsError(DomainError):
    """Ошибка конфликта email внутри tenant."""

    def __init__(self, email: str):
        """Формирует сообщение с занятым email."""
        super().__init__(f"User email '{email}' already exists in tenant.")


class PrimaryUserEmailNotFoundError(DomainError):
    """Ошибка отсутствия primary email пользователя."""

    def __init__(self, email: str):
        """Формирует сообщение с email, который не найден как primary."""
        super().__init__(f"Primary user email '{email}' was not found in tenant.")


class UserLoginUnavailableError(DomainError):
    """Ошибка недоступности пользователя для login."""

    def __init__(self):
        """Формирует сообщение о недоступности login."""
        super().__init__("User is not available for login.")


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
