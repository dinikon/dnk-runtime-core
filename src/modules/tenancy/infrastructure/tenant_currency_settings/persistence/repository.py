from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    TenantCurrencySettingsNotFoundError,
)
from src.modules.tenancy.infrastructure.persistence.models.tenant_currency_settings import (
    TENANT_CURRENCY_SETTINGS_ID,
    TenantCurrencySettingsModel,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.mapper import (
    TenantCurrencySettingsMapper,
)


class SqlAlchemyTenantCurrencySettingsRepository:
    """Хранит агрегат на заранее привязанном tenant-соединении общего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает внешнюю tenant-сессию без выбора схемы в SQL."""
        self._session = session

    async def get(self) -> TenantCurrencySettings | None:
        """Читает единственную запись текущей схемы и восстанавливает агрегат."""
        table = TenantCurrencySettingsModel.__table__
        result = await self._session.execute(
            select(table).where(table.c.id == TENANT_CURRENCY_SETTINGS_ID)
        )
        row = result.mappings().one_or_none()
        return None if row is None else TenantCurrencySettingsMapper.to_domain(row)

    async def initialize(self, settings: TenantCurrencySettings) -> None:
        """Заменяет миграционный default начальным состоянием нового Tenant."""
        table = TenantCurrencySettingsModel.__table__
        result = await self._session.execute(
            update(table)
            .where(table.c.id == TENANT_CURRENCY_SETTINGS_ID)
            .values(TenantCurrencySettingsMapper.to_update_values(settings))
        )
        if result.rowcount != 1:
            raise TenantCurrencySettingsNotFoundError(
                "Tenant currency settings are not migrated."
            )
