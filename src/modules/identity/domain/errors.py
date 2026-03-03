from src.modules.shared.domain.errors import ValidationError


class UserEmailAlreadyExistsError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"User email '{email}' already exists in tenant.")


class TenantHostNotFoundError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' is not available for login.")


class PrimaryUserEmailNotFoundError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"Primary user email '{email}' was not found in tenant.")


class UserLoginUnavailableError(ValidationError):
    def __init__(self):
        super().__init__("User is not available for login.")


class InvalidOtpChallengeError(ValidationError):
    def __init__(self):
        super().__init__("OTP challenge is invalid or expired.")


class InvalidOtpCodeError(ValidationError):
    def __init__(self):
        super().__init__("OTP code is invalid.")
