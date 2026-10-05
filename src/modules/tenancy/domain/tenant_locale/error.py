from src.modules.shared.domain.domain_error import DomainError


class InvalidTenantLocaleError(DomainError):
    """Код локали отсутствует в системном справочнике."""


class TenantLocaleAlreadySelectedError(DomainError):
    """Локаль уже выбрана текущим tenant."""


class TenantLocaleNotSelectedError(DomainError):
    """Локаль не выбрана текущим tenant."""
