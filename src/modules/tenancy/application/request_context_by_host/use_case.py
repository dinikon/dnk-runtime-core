from __future__ import annotations

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.application.request_context_by_host.dto import (
    GetTenantRequestContextByHostQueryDTO,
    TenantRequestContextDTO,
)


class GetTenantRequestContextByHostUseCase:
    def __init__(
        self,
        tenants_repository: TenantRepositoryProtocol,
        tenant_domains_repository: TenantDomainRepositoryProtocol,
    ):
        self._tenants_repository = tenants_repository
        self._tenant_domains_repository = tenant_domains_repository

    async def execute(
        self,
        dto: GetTenantRequestContextByHostQueryDTO,
    ) -> TenantRequestContextDTO | None:
        normalized_host = dto.host.strip().lower()
        if not normalized_host:
            return None

        tenant_domain = await self._tenant_domains_repository.get_by_host(
            normalized_host
        )
        if tenant_domain is None:
            return None

        tenant = await self._tenants_repository.get_by_id(tenant_domain.tenant_id)
        if tenant is None:
            return None

        api_host = await self._tenant_domains_repository.get_api_host_by_tenant_id(
            tenant.id
        )
        if api_host is None:
            api_host = tenant_domain.host

        return TenantRequestContextDTO(
            tenant_id=tenant.id,
            tenant_domain_id=tenant_domain.id,
            host=tenant_domain.host,
            tenant_status=tenant.status.value,
            domain_status=tenant_domain.status.value,
            api_host=api_host,
        )
