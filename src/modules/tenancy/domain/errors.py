from src.modules.shared.domain.errors import DomainError


class InvalidTenantNameError(DomainError):
    """Ошибка пустого имени tenant."""

    def __init__(self):
        """Формирует сообщение о пустом имени tenant."""
        super().__init__("Tenant name must not be empty.")


class InvalidTenantExternalIdError(DomainError):
    """Ошибка пустого external_id tenant."""

    def __init__(self):
        """Формирует сообщение о пустом external_id tenant."""
        super().__init__("Tenant external_id must not be empty.")


class InvalidTenantDomainHostError(DomainError):
    """Ошибка пустого host tenant domain."""

    def __init__(self):
        """Формирует сообщение о пустом host tenant domain."""
        super().__init__("Tenant domain host must not be empty.")


class TenantNameAlreadyExistsError(DomainError):
    """Ошибка конфликта имени tenant."""

    def __init__(self, name: str):
        """Формирует сообщение с занятым именем tenant."""
        super().__init__(f"Tenant with name '{name}' already exists.")


class TenantExternalIdAlreadyExistsError(DomainError):
    """Ошибка конфликта external_id tenant."""

    def __init__(self, external_id: str):
        """Формирует сообщение с занятым external_id tenant."""
        super().__init__(f"Tenant with external_id '{external_id}' already exists.")


class TenantDomainHostAlreadyExistsError(DomainError):
    """Ошибка конфликта host tenant domain."""

    def __init__(self, host: str):
        """Формирует сообщение с занятым host tenant domain."""
        super().__init__(f"Tenant domain host '{host}' already exists.")


class TenantHostNotFoundError(DomainError):
    """Ошибка отсутствия tenant для host."""

    def __init__(self, host: str):
        """Формирует сообщение с host, для которого tenant не найден."""
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(DomainError):
    """Ошибка недоступности login для tenant host."""

    def __init__(self, host: str):
        """Формирует сообщение с host, недоступным для login."""
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
