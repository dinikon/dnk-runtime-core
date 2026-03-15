from src.modules.shared.domain.errors import ValidationError


class TenantDomainHostAlreadyExistsError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant domain host '{host}' already exists.")


class TenantHostNotFoundError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' is not available for login.")
