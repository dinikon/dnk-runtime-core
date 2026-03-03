from src.modules.shared.domain.errors import ValidationError


class TenantNameAlreadyExistsError(ValidationError):
    def __init__(self, name: str):
        super().__init__(f"Tenant with name '{name}' already exists.")


class TenantDomainHostAlreadyExistsError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant domain host '{host}' already exists.")
