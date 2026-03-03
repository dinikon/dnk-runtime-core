from __future__ import annotations

from typing import Protocol

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantRepositoryProtocol,
)
from src.modules.tenancy.domain.entities import Tenant
from src.modules.tenancy.domain.errors import (
    TenantExternalIdAlreadyExistsError,
    TenantNameAlreadyExistsError,
)


class TenantServiceProtocol(Protocol):
    async def create_tenant(self, name: str, external_id: str) -> Tenant: ...


class TenantService:
    def __init__(self, tenants_repository: TenantRepositoryProtocol):
        self._tenants_repository = tenants_repository

    async def create_tenant(self, name: str, external_id: str) -> Tenant:
        normalized_name = name.strip()
        normalized_external_id = external_id.strip()
        if await self._tenants_repository.exists_by_name(normalized_name):
            raise TenantNameAlreadyExistsError(normalized_name)
        if await self._tenants_repository.exists_by_external_id(normalized_external_id):
            raise TenantExternalIdAlreadyExistsError(normalized_external_id)

        tenant = Tenant.create(
            name=normalized_name,
            external_id=normalized_external_id,
        )
        await self._tenants_repository.add(tenant)
        return tenant
