from src.modules.shared import DomainError


class InvalidTenantDomainHostError(DomainError):
    """Ошибка пустого host tenant domain."""

    def __init__(self) -> None:
        """Формирует сообщение о пустом host tenant domain."""
        super().__init__("Tenant domain host must not be empty.")


class TenantDomainHostAlreadyExistsError(DomainError):
    """Ошибка конфликта host tenant domain."""

    def __init__(self, host: str) -> None:
        """Формирует сообщение с занятым host tenant domain."""
        super().__init__(f"Tenant domain host '{host}' already exists.")


class TenantHostNotFoundError(DomainError):
    """Ошибка отсутствия tenant для host."""

    def __init__(self, host: str) -> None:
        """Формирует сообщение с host, для которого tenant не найден."""
        super().__init__(f"Tenant for host '{host}' was not found.")


class TenantLoginUnavailableError(DomainError):
    """Ошибка недоступности login для tenant host."""

    def __init__(self, host: str) -> None:
        """Формирует сообщение с host, недоступным для login."""
        super().__init__(f"Tenant for host '{host}' is not available for login.")


__all__ = [
    "InvalidTenantDomainHostError",
    "TenantDomainHostAlreadyExistsError",
    "TenantHostNotFoundError",
    "TenantLoginUnavailableError",
]
