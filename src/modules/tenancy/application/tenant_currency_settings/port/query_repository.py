from typing import Protocol

from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.dto import (
    GetTenantCurrencySettingsResultDTO,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO


class TenantCurrencySettingsQueryRepositoryProtocol(Protocol):
    """Порт чтения настроек валюты без восстановления Tenant."""

    async def get_currency_settings(
        self, tenant_id: TenantIdVO
    ) -> GetTenantCurrencySettingsResultDTO | None:
        """Возвращает базовую валюту Tenant или отсутствие записи."""
        ...
