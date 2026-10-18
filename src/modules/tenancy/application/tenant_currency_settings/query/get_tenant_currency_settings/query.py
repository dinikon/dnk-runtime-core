from dataclasses import dataclass

from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO


@dataclass(frozen=True, slots=True)
class GetTenantCurrencySettingsQuery:
    """Запрашивает базовую валюту конкретного Tenant из доверенного контекста."""

    tenant_id: TenantIdVO
