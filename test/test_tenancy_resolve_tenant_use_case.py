from __future__ import annotations

import unittest

from src.modules.tenancy.application.tenant_domain.query import (
    ResolveTenantByHostQuery,
)
from src.modules.tenancy.application.tenant_domain.use_case import (
    ResolveTenantByHostUseCase,
)
from src.modules.tenancy.domain.tenant import Tenant
from src.modules.tenancy.domain.tenant.value_object import TenantStatus
from src.modules.tenancy.domain.tenant_domain import TenantDomain, TenantDomainStatus


class _TenantRepositoryStub:
    def __init__(self, tenant: Tenant | None) -> None:
        self.tenant = tenant

    async def get_by_id(self, tenant_id):
        if self.tenant is None or self.tenant.id != tenant_id:
            return None
        return self.tenant


class _TenantDomainRepositoryStub:
    def __init__(
        self,
        *,
        domain: TenantDomain | None,
        api_host: str | None = "api.example.com",
    ) -> None:
        self.domain = domain
        self.api_host = api_host

    async def get_by_host(self, host: str):
        if self.domain is None or self.domain.host != host:
            return None
        return self.domain

    async def get_api_host_by_tenant_id(self, tenant_id):
        return self.api_host


class ResolveTenantByHostUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_result_includes_tenant_name(self) -> None:
        tenant = Tenant.create(name="Acme", external_id="acme")
        domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="console.example.com",
        )
        use_case = ResolveTenantByHostUseCase(
            tenants_repository=_TenantRepositoryStub(tenant),
            tenant_domains_repository=_TenantDomainRepositoryStub(domain=domain),
        )

        result = await use_case.execute(
            ResolveTenantByHostQuery(host="console.example.com")
        )

        self.assertTrue(result.exists)
        self.assertTrue(result.available)
        self.assertEqual(result.tenant_name, "Acme")

    async def test_availability_requires_active_tenant_and_domain(self) -> None:
        for tenant_status in TenantStatus:
            for domain_status in TenantDomainStatus:
                with self.subTest(tenant=tenant_status, domain=domain_status):
                    tenant = Tenant.create(name="Acme", external_id="acme")
                    tenant.status = tenant_status
                    domain = TenantDomain.create_primary_console_domain(
                        tenant_id=tenant.id,
                        host="tenant1.dniko.app",
                    )
                    domain.status = domain_status
                    use_case = ResolveTenantByHostUseCase(
                        tenants_repository=_TenantRepositoryStub(tenant),
                        tenant_domains_repository=_TenantDomainRepositoryStub(
                            domain=domain
                        ),
                    )

                    result = await use_case.execute(
                        ResolveTenantByHostQuery(host="tenant1.dniko.app")
                    )

                    self.assertEqual(
                        result.available,
                        tenant_status == TenantStatus.ACTIVE
                        and domain_status == TenantDomainStatus.ACTIVE,
                    )

    async def test_same_origin_domain_is_normalized_and_used_without_api_domain(
        self,
    ) -> None:
        tenant = Tenant.create(name="Acme", external_id="acme")
        domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="tenant1.dniko.app",
        )
        use_case = ResolveTenantByHostUseCase(
            tenants_repository=_TenantRepositoryStub(tenant),
            tenant_domains_repository=_TenantDomainRepositoryStub(
                domain=domain, api_host=None
            ),
        )

        result = await use_case.execute(
            ResolveTenantByHostQuery(host="TENANT1.dniko.app:443")
        )

        self.assertTrue(result.available)
        self.assertEqual(result.tenant_id, tenant.id.uuid)
        self.assertEqual(result.api_host, "tenant1.dniko.app")

    async def test_not_found_result_has_null_tenant_name(self) -> None:
        use_case = ResolveTenantByHostUseCase(
            tenants_repository=_TenantRepositoryStub(None),
            tenant_domains_repository=_TenantDomainRepositoryStub(domain=None),
        )

        result = await use_case.execute(
            ResolveTenantByHostQuery(host="missing.example.com")
        )

        self.assertFalse(result.exists)
        self.assertFalse(result.available)
        self.assertEqual(result.status, "not_found")
        self.assertIsNone(result.tenant_name)


__all__ = ["ResolveTenantByHostUseCaseTests"]
