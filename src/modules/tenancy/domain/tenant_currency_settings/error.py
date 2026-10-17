from src.modules.shared.domain.domain_error import DomainError


class InvalidTenantBaseCurrencyError(DomainError):
    """Базовая валюта настроек Tenant должна быть CurrencyVO."""


class TenantCurrencySettingsNotFoundError(DomainError):
    """Валютные настройки отсутствуют в tenant-схеме."""
