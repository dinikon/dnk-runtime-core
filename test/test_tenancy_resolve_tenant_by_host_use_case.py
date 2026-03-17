from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from src.modules.tenancy.application.queries import ResolveTenantByHostQuery
from src.modules.tenancy.application.use_cases.resolve_tenant_by_host import (
    ResolveTenantByHostUseCase,
)
from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.value_objects import TenantStatus


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
        api_hosts: dict[UUID, str] | None = None,
    ) -> None:
        self._domains = domains
        self._api_hosts = api_hosts or {}

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
        return self._api_hosts.get(tenant_id)

    async def exists_by_host(self, host: str) -> bool:
        return any(domain.host == host for domain in self._domains)


class TestResolveTenantByHostUseCase(unittest.IsolatedAsyncioTestCase):
    async def test_execute_returns_not_found_for_empty_host(self) -> None:
        use_case = ResolveTenantByHostUseCase(
            tenants_repository=FakeTenantRepository([]),
            tenant_domains_repository=FakeTenantDomainRepository([]),
        )

        result = await use_case.execute(ResolveTenantByHostQuery(host="  "))

        self.assertFalse(result.exists)
        self.assertFalse(result.available)
        self.assertEqual(result.status, "not_found")
        self.assertIsNone(result.tenant_id)
        self.assertIsNone(result.api_host)

    async def test_execute_returns_active_tenant(self) -> None:
        tenant = Tenant.create(name="Acme", external_id="acme-ext")
        domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="console.acme.local",
        )
        use_case = ResolveTenantByHostUseCase(
            tenants_repository=FakeTenantRepository([tenant]),
            tenant_domains_repository=FakeTenantDomainRepository(
                [domain],
                api_hosts={tenant.id: "http.acme.local"},
            ),
        )

        result = await use_case.execute(
            ResolveTenantByHostQuery(host="Console.Acme.local:443")
        )

        self.assertTrue(result.exists)
        self.assertTrue(result.available)
        self.assertEqual(result.status, "active")
        self.assertEqual(result.tenant_id, tenant.id)
        self.assertEqual(result.api_host, "http.acme.local")

    async def test_execute_returns_unavailable_for_freeze_tenant(self) -> None:
        tenant = Tenant.create(name="Acme", external_id="acme-ext")
        tenant.status = TenantStatus.FREEZE
        domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="console.acme.local",
        )
        use_case = ResolveTenantByHostUseCase(
            tenants_repository=FakeTenantRepository([tenant]),
            tenant_domains_repository=FakeTenantDomainRepository([domain]),
        )

        result = await use_case.execute(
            ResolveTenantByHostQuery(host="console.acme.local")
        )

        self.assertTrue(result.exists)
        self.assertFalse(result.available)
        self.assertEqual(result.status, "freeze")
