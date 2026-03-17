from src.modules.shared.domain.errors import DomainError


class InvalidTenantNameError(DomainError):
    def __init__(self):
        super().__init__("Tenant name must not be empty.")


class InvalidTenantExternalIdError(DomainError):
    def __init__(self):
        super().__init__("Tenant external_id must not be empty.")


class InvalidTenantDomainHostError(DomainError):
    def __init__(self):
        super().__init__("Tenant domain host must not be empty.")


class TenantNameAlreadyExistsError(DomainError):
    def __init__(self, name: str):
        super().__init__(f"Tenant with name '{name}' already exists.")


class TenantExternalIdAlreadyExistsError(DomainError):
    def __init__(self, external_id: str):
        super().__init__(f"Tenant with external_id '{external_id}' already exists.")


class TenantDomainHostAlreadyExistsError(DomainError):
    def __init__(self, host: str):
        super().__init__(f"Tenant domain host '{host}' already exists.")


class TenantHostNotFoundError(DomainError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(DomainError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' is not available for login.")


__all__ = [
    "InvalidTenantDomainHostError",
    "InvalidTenantExternalIdError",
    "InvalidTenantNameError",
    "TenantDomainHostAlreadyExistsError",
    "TenantExternalIdAlreadyExistsError",
    "TenantHostNotFoundError",
    "TenantLoginUnavailableError",
    "TenantNameAlreadyExistsError",
]
