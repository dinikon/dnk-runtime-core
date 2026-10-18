from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    InvalidTenantBaseCurrencyError,
)


@dataclass(slots=True)
class TenantCurrencySettings:
    """Единственный агрегат валютных настроек в tenant-схеме."""

    _base_currency: CurrencyVO
    created_at: datetime
    updated_at: datetime

    @property
    def base_currency(self) -> CurrencyVO:
        """Возвращает базовую валюту без операции её изменения в MVP."""
        return self._base_currency

    @classmethod
    def create(cls, *, base_currency: CurrencyVO) -> "TenantCurrencySettings":
        """Создаёт начальные настройки для нового Tenant после проверки справочника."""
        if not isinstance(base_currency, CurrencyVO):
            raise InvalidTenantBaseCurrencyError("Base currency must be CurrencyVO.")
        now = datetime.now(UTC)
        return cls(base_currency, now, now)

    @classmethod
    def restore(
        cls, *, base_currency: CurrencyVO, created_at: datetime, updated_at: datetime
    ) -> "TenantCurrencySettings":
        """Восстанавливает сохранённые настройки без событий создания."""
        if not isinstance(base_currency, CurrencyVO):
            raise InvalidTenantBaseCurrencyError("Base currency must be CurrencyVO.")
        return cls(base_currency, created_at, updated_at)
