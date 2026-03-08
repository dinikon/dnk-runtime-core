from uuid import UUID

from src.modules.shared.domain.errors import ValidationError


class TenantNameAlreadyExistsError(ValidationError):
    def __init__(self, name: str):
        super().__init__(f"Tenant with name '{name}' already exists.")


class TenantExternalIdAlreadyExistsError(ValidationError):
    def __init__(self, external_id: str):
        super().__init__(f"Tenant with external_id '{external_id}' already exists.")


class TenantDomainHostAlreadyExistsError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant domain host '{host}' already exists.")


class TenantHostNotFoundError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(ValidationError):
    def __init__(self, host: str):
        super().__init__(f"Tenant for host '{host}' is not available for login.")


class TenantDataSourceAlreadyExistsError(ValidationError):
    def __init__(self, tenant_id: UUID):
        super().__init__(f"Tenant data source for tenant '{tenant_id}' already exists.")


class TenantDataSourceSchemaAlreadyExistsError(ValidationError):
    def __init__(self, schema: str):
        super().__init__(f"Tenant data source schema '{schema}' already exists.")
