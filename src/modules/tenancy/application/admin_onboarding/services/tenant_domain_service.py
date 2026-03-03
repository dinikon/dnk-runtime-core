from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDomainRepositoryProtocol,
)
from src.modules.tenancy.domain.entities import TenantDomain
from src.modules.tenancy.domain.errors import TenantDomainHostAlreadyExistsError


class TenantDomainServiceProtocol(Protocol):
    async def create_primary_domain(
        self,
        tenant_id: UUID,
        host: str,
    ) -> TenantDomain: ...


class TenantDomainService:
    def __init__(self, tenant_domains_repository: TenantDomainRepositoryProtocol):
        self._tenant_domains_repository = tenant_domains_repository

    async def create_primary_domain(
        self,
        tenant_id: UUID,
        host: str,
    ) -> TenantDomain:
        normalized_host = host.strip().lower()
        if await self._tenant_domains_repository.exists_by_host(normalized_host):
            raise TenantDomainHostAlreadyExistsError(normalized_host)

        tenant_domain = TenantDomain.create_primary(
            tenant_id=tenant_id,
            host=normalized_host,
        )
        await self._tenant_domains_repository.add(tenant_domain)
        return tenant_domain
