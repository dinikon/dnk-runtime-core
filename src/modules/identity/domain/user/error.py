from src.modules.shared import DomainError


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


__all__ = [
    "PrimaryUserEmailNotFoundError",
    "UserEmailAlreadyExistsError",
    "UserLoginUnavailableError",
]
