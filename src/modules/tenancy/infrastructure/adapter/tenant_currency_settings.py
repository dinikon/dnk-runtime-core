from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.repository import (
    SqlAlchemyTenantCurrencySettingsRepository,
)


class TenantCurrencySettingsPersistenceAdapter:
    """Собирает запись настроек после создания схемы, сохраняя общий UoW onboarding."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        """Принимает внешнюю сессию и стратегию схем без выдачи SQL в Application."""
        self._session = session
        self._naming = naming

    async def initialize(
        self, tenant_id: TenantIdVO, settings: TenantCurrencySettings
    ) -> None:
        """Привязывает схему снаружи репозитория и сохраняет начальный агрегат."""
        connection = await self._session.connection()
        await bind_tenant_schema(connection, tenant_id.uuid, self._naming)
        await SqlAlchemyTenantCurrencySettingsRepository(self._session).initialize(
            settings
        )
