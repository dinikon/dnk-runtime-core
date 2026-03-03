from __future__ import annotations

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.application.resolve_tenant_by_host.dto import (
    ResolveTenantByHostQueryDTO,
    ResolveTenantByHostResultDTO,
)
from src.modules.tenancy.domain.value_objects.tenant_status import TenantStatus


class ResolveTenantByHostUseCase:
    def __init__(
        self,
        tenants_repository: TenantRepositoryProtocol,
        tenant_domains_repository: TenantDomainRepositoryProtocol,
    ):
        self._tenants_repository = tenants_repository
        self._tenant_domains_repository = tenant_domains_repository

    async def execute(
        self,
        dto: ResolveTenantByHostQueryDTO,
    ) -> ResolveTenantByHostResultDTO:
        normalized_host = dto.host.strip().lower()
        if not normalized_host:
            return ResolveTenantByHostResultDTO(
                exists=False,
                available=False,
                status="not_found",
                tenant_id=None,
                api_host=None,
            )

        tenant_domain = await self._tenant_domains_repository.get_by_host(
            normalized_host
        )
        if tenant_domain is None:
            return ResolveTenantByHostResultDTO(
                exists=False,
                available=False,
                status="not_found",
                tenant_id=None,
                api_host=None,
            )

        tenant = await self._tenants_repository.get_by_id(tenant_domain.tenant_id)
        if tenant is None:
            return ResolveTenantByHostResultDTO(
                exists=False,
                available=False,
                status="not_found",
                tenant_id=None,
                api_host=None,
            )

        api_host = await self._tenant_domains_repository.get_api_host_by_tenant_id(
            tenant.id
        )
        if api_host is None:
            api_host = tenant_domain.host

        return ResolveTenantByHostResultDTO(
            exists=True,
            available=tenant.status == TenantStatus.ACTIVE,
            status=tenant.status.value,
            tenant_id=tenant.id,
            api_host=api_host,
        )
