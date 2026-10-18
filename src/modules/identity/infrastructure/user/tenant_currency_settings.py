from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.handler import (
    GetTenantCurrencySettingsHandler,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.query import (
    GetTenantCurrencySettingsQuery,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyVO


class TenancyProfileCurrencySettingsAdapter:
    """Адаптирует публичный Query Tenancy к порту базовой валюты Identity."""

    def __init__(self, handler: GetTenantCurrencySettingsHandler) -> None:
        """Принимает сценарий Tenancy, собранный на общем tenant UoW."""
        self._handler = handler

    async def get_base_currency(self, tenant_id: EntityIdVO) -> CurrencyVO:
        """Возвращает базовую валюту без импорта агрегата и SQL-модели Tenancy."""
        result = await self._handler.execute(
            GetTenantCurrencySettingsQuery(TenantIdVO.from_value(tenant_id.uuid))
        )
        return CurrencyVO.from_value(result.base_currency)
