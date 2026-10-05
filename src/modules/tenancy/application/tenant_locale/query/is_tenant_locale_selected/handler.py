from src.modules.tenancy.application.tenant_locale.port.query_repository import (
    TenantLocaleQueryRepositoryProtocol,
)
from src.modules.tenancy.application.tenant_locale.query.is_tenant_locale_selected.dto import (
    IsTenantLocaleSelectedDTO,
)
from src.modules.tenancy.application.tenant_locale.query.is_tenant_locale_selected.query import (
    IsTenantLocaleSelectedQuery,
)
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)


class IsTenantLocaleSelectedHandler:
    """Публичный Application-сценарий проверки локали текущего tenant."""

    def __init__(self, repository: TenantLocaleQueryRepositoryProtocol):
        self._repository = repository

    async def execute(
        self, query: IsTenantLocaleSelectedQuery
    ) -> IsTenantLocaleSelectedDTO:
        code = TenantLocaleCodeVO(query.code)
        return IsTenantLocaleSelectedDTO(await self._repository.contains(code))
