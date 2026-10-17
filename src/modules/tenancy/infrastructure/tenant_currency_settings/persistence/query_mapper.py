from collections.abc import Mapping
from typing import Any

from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.dto import (
    GetTenantCurrencySettingsResultDTO,
)


class TenantCurrencySettingsQueryMapper:
    """Преобразует SQL-проекцию валютной настройки в DTO сценария чтения."""

    @staticmethod
    def to_currency_settings(
        row: Mapping[str, Any],
    ) -> GetTenantCurrencySettingsResultDTO:
        """Создаёт DTO без восстановления агрегата и внешних обращений."""
        return GetTenantCurrencySettingsResultDTO(base_currency=row["base_currency"])
