from typing import Protocol
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProfileTenantCurrencySettingsProtocol(Protocol):
    """Читает базовую валюту доверенного Tenant через публичный контракт Tenancy."""

    async def get_base_currency(self, tenant_id: EntityIdVO) -> CurrencyVO:
        """Возвращает обязательную базовую валюту либо сообщает об отсутствии настроек."""
        ...
