class ValidationError(ValueError):
    """Base domain validation error."""


class TenantNameAlreadyExistsError(ValidationError):
    def __init__(self, name: str):
        super().__init__(f"Tenant with name '{name}' already exists.")


class UserEmailAlreadyExistsError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"User email '{email}' already exists in tenant.")


class TenantDomainHostAlreadyExistsError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant domain host '{host}' already exists.")
