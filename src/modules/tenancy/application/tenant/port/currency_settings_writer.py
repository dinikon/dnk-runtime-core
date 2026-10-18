from typing import Protocol

from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)


class TenantCurrencySettingsWriterProtocol(Protocol):
    """Порт onboarding для записи агрегата в только что созданную tenant-схему."""

    async def initialize(
        self, tenant_id: TenantIdVO, settings: TenantCurrencySettings
    ) -> None:
        """Привязывает подготовленное хранилище и записывает начальные настройки."""
        ...
