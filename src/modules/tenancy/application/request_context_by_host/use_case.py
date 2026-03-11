from __future__ import annotations

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.application.request_context_by_host.dto import (
    ResolveTenantRequestContextByHostQueryDTO,
    TenantRequestContextDTO,
)
from src.modules.tenancy.domain.errors import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)
from src.modules.tenancy.domain.value_objects.tenant_domain_status import (
    TenantDomainStatus,
)
from src.modules.shared.http.host import normalize_host


class ResolveTenantRequestContextByHostUseCase:
    def __init__(
        self,
        tenants_repository: TenantRepositoryProtocol,
        tenant_domains_repository: TenantDomainRepositoryProtocol,
    ):
        self._tenants_repository = tenants_repository
        self._tenant_domains_repository = tenant_domains_repository

    async def execute(
        self,
        dto: ResolveTenantRequestContextByHostQueryDTO,
    ) -> TenantRequestContextDTO:
        normalized_host = normalize_host(dto.host)
        if not normalized_host:
            raise TenantHostNotFoundError(normalized_host)

        tenant_domain = await self._tenant_domains_repository.get_by_host(
            normalized_host
        )
        if tenant_domain is None:
            raise TenantHostNotFoundError(normalized_host)

        tenant = await self._tenants_repository.get_by_id(tenant_domain.tenant_id)
        if tenant is None:
            raise TenantHostNotFoundError(normalized_host)
        if (
            tenant_domain.status != TenantDomainStatus.ACTIVE
            or not tenant.allows_login()
        ):
            raise TenantLoginUnavailableError(normalized_host)

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
