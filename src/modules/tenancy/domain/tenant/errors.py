from src.modules.shared.domain.errors import ValidationError


class TenantNameAlreadyExistsError(ValidationError):
    def __init__(self, name: str):
        super().__init__(f"Tenant with name '{name}' already exists.")


class TenantExternalIdAlreadyExistsError(ValidationError):
    def __init__(self, external_id: str):
        super().__init__(f"Tenant with external_id '{external_id}' already exists.")
