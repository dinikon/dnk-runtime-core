from src.modules.shared.domain.errors import DomainError


class TenantDomainHostAlreadyExistsError(DomainError):
    def __init__(self, host: str):
        super().__init__(f"Tenant domain host '{host}' already exists.")


class TenantHostNotFoundError(DomainError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(DomainError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' is not available for login.")
