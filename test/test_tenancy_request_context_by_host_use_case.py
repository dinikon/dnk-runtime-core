from __future__ import annotations

import unittest
from uuid import UUID

from src.modules.tenancy.application.queries import (
    ResolveTenantRequestContextByHostQuery,
)
from src.modules.tenancy.application.use_cases.resolve_tenant_request_context_by_host import (
    ResolveTenantRequestContextByHostUseCase,
)
from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.errors import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)
from src.modules.tenancy.domain.value_objects import TenantDomainStatus


class FakeTenantRepository:
    def __init__(self, tenants: list[Tenant]):
        self._tenants = tenants

    async def add(self, tenant: Tenant) -> None:
        self._tenants.append(tenant)

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        for tenant in self._tenants:
            if tenant.id == tenant_id:
                return tenant
        return None

    async def get_by_name(self, name: str) -> Tenant | None:
        for tenant in self._tenants:
            if tenant.name == name:
                return tenant
        return None

    async def exists_by_external_id(self, external_id: str) -> bool:
        return any(tenant.external_id == external_id for tenant in self._tenants)

    async def exists_by_name(self, name: str) -> bool:
        return any(tenant.name == name for tenant in self._tenants)


class FakeTenantDomainRepository:
    def __init__(
        self,
        domains: list[TenantDomain],
        api_host: str | None = None,
    ) -> None:
        self._domains = domains
        self._api_host = api_host

    async def add(self, domain: TenantDomain) -> None:
        self._domains.append(domain)

    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None:
        for domain in self._domains:
            if domain.id == domain_id:
                return domain
        return None

    async def get_by_host(self, host: str) -> TenantDomain | None:
        for domain in self._domains:
            if domain.host == host:
                return domain
        return None

    async def get_api_host_by_tenant_id(self, tenant_id: UUID) -> str | None:
        return self._api_host

    async def exists_by_host(self, host: str) -> bool:
        return any(domain.host == host for domain in self._domains)


class TestResolveTenantRequestContextByHostUseCase(unittest.IsolatedAsyncioTestCase):
    async def test_execute_returns_request_context(self) -> None:
        tenant = Tenant.create(name="Acme", external_id="acme-ext")
        domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="console.acme.local",
        )
        use_case = ResolveTenantRequestContextByHostUseCase(
            tenants_repository=FakeTenantRepository([tenant]),
            tenant_domains_repository=FakeTenantDomainRepository(
                [domain],
                api_host="api.acme.local",
            ),
        )

        result = await use_case.execute(
            ResolveTenantRequestContextByHostQuery(host="Console.Acme.local")
        )

        self.assertEqual(result.tenant_id, tenant.id)
        self.assertEqual(result.tenant_domain_id, domain.id)
        self.assertEqual(result.host, "console.acme.local")
        self.assertEqual(result.tenant_status, "active")
        self.assertEqual(result.domain_status, "active")
        self.assertEqual(result.api_host, "api.acme.local")

    async def test_execute_raises_not_found_for_unknown_host(self) -> None:
        use_case = ResolveTenantRequestContextByHostUseCase(
            tenants_repository=FakeTenantRepository([]),
            tenant_domains_repository=FakeTenantDomainRepository([]),
        )

        with self.assertRaises(TenantHostNotFoundError):
            await use_case.execute(
                ResolveTenantRequestContextByHostQuery(host="unknown.local")
            )

    async def test_execute_raises_login_unavailable_for_inactive_domain(self) -> None:
        tenant = Tenant.create(name="Acme", external_id="acme-ext")
        domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="console.acme.local",
        )
        domain.status = TenantDomainStatus.DISABLED
        use_case = ResolveTenantRequestContextByHostUseCase(
            tenants_repository=FakeTenantRepository([tenant]),
            tenant_domains_repository=FakeTenantDomainRepository([domain]),
        )

        with self.assertRaises(TenantLoginUnavailableError):
            await use_case.execute(
                ResolveTenantRequestContextByHostQuery(host="console.acme.local")
            )

