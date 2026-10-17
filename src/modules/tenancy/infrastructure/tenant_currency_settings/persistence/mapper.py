from collections.abc import Mapping
from typing import Any

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)


class TenantCurrencySettingsMapper:
    """Преобразует агрегат настроек и SQL-представление без I/O."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> TenantCurrencySettings:
        """Восстанавливает агрегат через явную фабрику."""
        return TenantCurrencySettings.restore(
            base_currency=CurrencyVO.from_value(row["base_currency"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def to_update_values(settings: TenantCurrencySettings) -> dict[str, Any]:
        """Извлекает начальное состояние для onboarding без правил смены валюты."""
        return {
            "base_currency": settings.base_currency.value,
            "created_at": settings.created_at,
            "updated_at": settings.updated_at,
        }
