from src.modules.shared.domain.domain_error import DomainError


class TenantSchemaAlreadyExistsError(DomainError):
    """Новая tenant-схема конфликтует с существующей схемой."""

    def __init__(self, schema_name: str) -> None:
        super().__init__(f"Tenant schema '{schema_name}' already exists.")
