from src.modules.shared.application.network.host import normalize_host
from src.modules.tenancy.application.tenant_domain.query.resolve_readable_tenant_by_host.dto import (
    ResolveReadableTenantByHostResultDTO,
)
from src.modules.tenancy.application.tenant_domain.query.resolve_readable_tenant_by_host.query import (
    ResolveReadableTenantByHostQuery,
)
from src.modules.tenancy.domain.tenant.repository import TenantRepositoryProtocol
from src.modules.tenancy.domain.tenant_domain.repository import (
    TenantDomainRepositoryProtocol,
)
from src.modules.tenancy.domain.tenant_domain.value_object.tenant_domain_status import (
    TenantDomainStatus,
)


class ResolveReadableTenantByHostHandler:
    """Находит tenant с активным доменом и разрешённым чтением данных."""

    def __init__(
        self,
        tenants: TenantRepositoryProtocol,
        domains: TenantDomainRepositoryProtocol,
    ) -> None:
        """Принимает репозитории Tenancy на общей сессии запроса."""
        self._tenants = tenants
        self._domains = domains

    async def execute(
        self, query: ResolveReadableTenantByHostQuery
    ) -> ResolveReadableTenantByHostResultDTO | None:
        """Разрешает хост по правилу чтения данных tenant."""
        host = normalize_host(query.host)
        if not host:
            return None
        domain = await self._domains.get_by_host(host)
        if domain is None or domain.status != TenantDomainStatus.ACTIVE:
            return None
        tenant = await self._tenants.get_by_id(domain.tenant_id)
        if tenant is None or not tenant.allows_read_business_data():
            return None
        return ResolveReadableTenantByHostResultDTO(tenant_id=tenant.id.uuid)
