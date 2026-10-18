from src.modules.tenancy.application.tenant_currency_settings.port.query_repository import (
    TenantCurrencySettingsQueryRepositoryProtocol,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.dto import (
    GetTenantCurrencySettingsResultDTO,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.query import (
    GetTenantCurrencySettingsQuery,
)
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    TenantCurrencySettingsNotFoundError,
)


class GetTenantCurrencySettingsHandler:
    """Предоставляет публичный контракт чтения базовой валюты Tenant."""

    def __init__(
        self, repository: TenantCurrencySettingsQueryRepositoryProtocol
    ) -> None:
        """Принимает абстрактный порт SQL-проекции на внешней сессии."""
        self._repository = repository

    async def execute(
        self, query: GetTenantCurrencySettingsQuery
    ) -> GetTenantCurrencySettingsResultDTO:
        """Возвращает настройки или сообщает об отсутствии Tenant."""
        result = await self._repository.get_currency_settings(query.tenant_id)
        if result is None:
            raise TenantCurrencySettingsNotFoundError(
                "Tenant currency settings not found."
            )
        return result
