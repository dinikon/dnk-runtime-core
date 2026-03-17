from __future__ import annotations

from src.modules.shared.http.host import normalize_host
from src.modules.tenancy.application.dto import ResolveTenantByHostResultDTO
from src.modules.tenancy.application.queries import ResolveTenantByHostQuery
from src.modules.tenancy.domain.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)


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
        query: ResolveTenantByHostQuery,
    ) -> ResolveTenantByHostResultDTO:
        normalized_host = normalize_host(query.host)
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
            available=tenant.allows_login(),
            status=tenant.status.value,
            tenant_id=tenant.id,
            api_host=api_host,
        )


__all__ = ["ResolveTenantByHostUseCase"]
