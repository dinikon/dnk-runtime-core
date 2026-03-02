from __future__ import annotations

from typing import Protocol

from src.application.admin_tenants.ports.repositories import TenantRepositoryProtocol
from src.domain.common.errors import TenantNameAlreadyExistsError
from src.domain.tenancy.entities import Tenant


class TenantServiceProtocol(Protocol):
    async def create_tenant(self, name: str) -> Tenant: ...


class TenantService:
    def __init__(self, tenants_repository: TenantRepositoryProtocol):
        self._tenants_repository = tenants_repository

    async def create_tenant(self, name: str) -> Tenant:
        normalized_name = name.strip()
        if await self._tenants_repository.exists_by_name(normalized_name):
            raise TenantNameAlreadyExistsError(normalized_name)

        tenant = Tenant.create(name=normalized_name)
        await self._tenants_repository.add(tenant)
        return tenant
