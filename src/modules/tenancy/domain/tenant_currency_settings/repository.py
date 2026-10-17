from typing import Protocol

from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)


class TenantCurrencySettingsRepositoryProtocol(Protocol):
    """Хранит агрегат настроек на соединении одного tenant без выбора схемы."""

    async def get(self) -> TenantCurrencySettings | None:
        """Восстанавливает единственный агрегат из текущей tenant-схемы."""
        ...

    async def initialize(self, settings: TenantCurrencySettings) -> None:
        """Сохраняет начальное состояние в уже подготовленной схеме без commit."""
        ...
