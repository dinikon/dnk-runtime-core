from src.modules.tenancy.application.tenant_locale.query.list_tenant_locales.dto import (
    TenantLocaleDTO,
)
from src.modules.tenancy.application.tenant_locale.query.list_tenant_locales.query import (
    ListTenantLocalesQuery,
)
from src.modules.tenancy.application.tenant_locale.port.query_repository import (
    TenantLocaleQueryRepositoryProtocol,
)


class ListTenantLocalesHandler:
    """Читает выбранные локали текущей tenant-схемы."""

    def __init__(self, repository: TenantLocaleQueryRepositoryProtocol):
        self._repository = repository

    async def execute(self, query: ListTenantLocalesQuery) -> list[TenantLocaleDTO]:
        return [
            TenantLocaleDTO(item.code, item.created_at, item.created_by)
            for item in await self._repository.list_all()
        ]
