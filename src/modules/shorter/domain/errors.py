from src.modules.shared.domain.errors import ValidationError


class LinkCodeRequiredError(ValidationError):
    def __init__(self):
        super().__init__("link code is required")


class LinkCodeAlreadyExistsError(ValidationError):
    def __init__(self, *, domain_id: str, code: str):
        super().__init__(
            f"link code already exists: domain_id={domain_id}, code={code}"
        )


class LinkCodeLengthNotSupportedError(ValidationError):
    def __init__(self, *, length: int):
        super().__init__(
            f"link code length '{length}' is not supported; expected one of: 4, 6, 8, 16"
        )


class LinkCodeGenerationAttemptsExceededError(ValidationError):
    def __init__(self, *, domain_id: str, attempts: int):
        super().__init__(
            f"could not generate unique link code for domain '{domain_id}' in {attempts} attempts"
        )


class RedirectTargetUrlInvalidError(ValidationError):
    def __init__(self, *, target_url: str):
        super().__init__(
            f"redirect target_url must be a valid https URL, got '{target_url}'"
        )


class RedirectNotFoundError(ValidationError):
    def __init__(self, *, redirect_id: str):
        super().__init__(f"redirect '{redirect_id}' was not found")


__all__ = [
    "LinkCodeAlreadyExistsError",
    "LinkCodeGenerationAttemptsExceededError",
    "LinkCodeLengthNotSupportedError",
    "LinkCodeRequiredError",
    "RedirectNotFoundError",
    "RedirectTargetUrlInvalidError",
]
