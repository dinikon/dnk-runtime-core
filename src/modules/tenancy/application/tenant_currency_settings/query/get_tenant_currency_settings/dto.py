from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetTenantCurrencySettingsResultDTO:
    """Публичная проекция базовой валюты Tenant без агрегата и ORM."""

    base_currency: str
