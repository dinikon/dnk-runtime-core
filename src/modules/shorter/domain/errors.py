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


__all__ = [
    "LinkCodeAlreadyExistsError",
    "LinkCodeGenerationAttemptsExceededError",
    "LinkCodeLengthNotSupportedError",
    "LinkCodeRequiredError",
]
