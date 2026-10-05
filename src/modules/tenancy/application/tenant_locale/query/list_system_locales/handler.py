from src.modules.tenancy.application.tenant_locale.query.list_system_locales.dto import (
    SystemLocaleDTO,
)
from src.modules.tenancy.application.tenant_locale.query.list_system_locales.query import (
    ListSystemLocalesQuery,
)
from src.modules.tenancy.domain.tenant_locale.system_locales import SYSTEM_LOCALES


class ListSystemLocalesHandler:
    """Возвращает разрешённые коды без обращения к БД."""

    async def execute(self, query: ListSystemLocalesQuery) -> list[SystemLocaleDTO]:
        return [SystemLocaleDTO(item.code, item.name) for item in SYSTEM_LOCALES]
