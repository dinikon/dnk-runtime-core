from src.modules.shared.domain.errors import DomainError


class UserEmailAlreadyExistsError(DomainError):
    def __init__(self, email: str):
        super().__init__(f"User email '{email}' already exists in tenant.")


class PrimaryUserEmailNotFoundError(DomainError):
    def __init__(self, email: str):
        super().__init__(f"Primary user email '{email}' was not found in tenant.")


class UserLoginUnavailableError(DomainError):
    def __init__(self):
        super().__init__("User is not available for login.")


class InvalidOtpChallengeError(DomainError):
    def __init__(self):
        super().__init__("OTP challenge is invalid or expired.")


class InvalidOtpCodeError(DomainError):
    def __init__(self):
        super().__init__("OTP code is invalid.")


class InvalidSessionError(DomainError):
    def __init__(self):
        super().__init__("Session is invalid or expired.")
