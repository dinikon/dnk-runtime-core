from src.modules.shared.domain.errors import DomainError


class InvalidTenantNameError(DomainError):
    """Ошибка пустого имени tenant."""

    def __init__(self) -> None:
        """Формирует сообщение о пустом имени tenant."""
        super().__init__("Tenant name must not be empty.")


class InvalidTenantExternalIdError(DomainError):
    """Ошибка пустого external_id tenant."""

    def __init__(self) -> None:
        """Формирует сообщение о пустом external_id tenant."""
        super().__init__("Tenant external_id must not be empty.")


class TenantNameAlreadyExistsError(DomainError):
    """Ошибка конфликта имени tenant."""

    def __init__(self, name: str) -> None:
        """Формирует сообщение с занятым именем tenant."""
        super().__init__(f"Tenant with name '{name}' already exists.")


class TenantExternalIdAlreadyExistsError(DomainError):
    """Ошибка конфликта external_id tenant."""

    def __init__(self, external_id: str) -> None:
        """Формирует сообщение с занятым external_id tenant."""
        super().__init__(f"Tenant with external_id '{external_id}' already exists.")


__all__ = [
    "InvalidTenantExternalIdError",
    "InvalidTenantNameError",
    "TenantExternalIdAlreadyExistsError",
    "TenantNameAlreadyExistsError",
]
