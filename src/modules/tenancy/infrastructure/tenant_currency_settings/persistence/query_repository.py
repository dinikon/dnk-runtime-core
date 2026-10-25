from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.dto import (
    GetTenantCurrencySettingsResultDTO,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.persistence.models.tenant_currency_settings import (
    TENANT_CURRENCY_SETTINGS_ID,
    TenantCurrencySettingsModel,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.query_mapper import (
    TenantCurrencySettingsQueryMapper,
)


class SqlAlchemyTenantCurrencySettingsQueryRepository:
    """Читает настройки из заранее привязанной схемы доверенного Tenant."""

    def __init__(self, session: AsyncSession, tenant_id: TenantIdVO) -> None:
        """Принимает общую сессию UoW без самостоятельного commit."""
        self._session = session
        self._tenant_id = tenant_id

    async def get_currency_settings(
        self, tenant_id: TenantIdVO
    ) -> GetTenantCurrencySettingsResultDTO | None:
        """Возвращает проекцию строго для переданного Tenant ID."""
        if tenant_id != self._tenant_id:
            return None
        settings = TenantCurrencySettingsModel.__table__
        result = await self._session.execute(
            select(settings.c.base_currency).where(
                settings.c.id == TENANT_CURRENCY_SETTINGS_ID
            )
        )
        row = result.mappings().one_or_none()
        return (
            None
            if row is None
            else TenantCurrencySettingsQueryMapper.to_currency_settings(row)
        )
