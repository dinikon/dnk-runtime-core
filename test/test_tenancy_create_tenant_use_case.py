from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from src.modules.tenancy.application.commands import CreateTenantCommand
from src.modules.tenancy.application.ports.identity import ProvisionedTenantAdmin
from src.modules.tenancy.application.use_cases.create_tenant import CreateTenantUseCase
from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.errors import (
    InvalidTenantDomainHostError,
    TenantNameAlreadyExistsError,
)


class FakeUoW:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> "FakeUoW":
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeTenantRepository:
    def __init__(self) -> None:
        self.saved: list[Tenant] = []
        self._names: set[str] = set()
        self._external_ids: set[str] = set()

    async def add(self, tenant: Tenant) -> None:
        self.saved.append(tenant)
        self._names.add(tenant.name)
        self._external_ids.add(tenant.external_id)

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        for tenant in self.saved:
            if tenant.id == tenant_id:
                return tenant
        return None

    async def get_by_name(self, name: str) -> Tenant | None:
        for tenant in self.saved:
            if tenant.name == name:
                return tenant
        return None

    async def exists_by_external_id(self, external_id: str) -> bool:
        return external_id in self._external_ids

    async def exists_by_name(self, name: str) -> bool:
        return name in self._names


class FakeTenantDomainRepository:
    def __init__(self) -> None:
        self.saved: list[TenantDomain] = []
        self._hosts: set[str] = set()

    async def add(self, domain: TenantDomain) -> None:
        self.saved.append(domain)
        self._hosts.add(domain.host)

    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None:
        for domain in self.saved:
            if domain.id == domain_id:
                return domain
        return None

    async def get_by_host(self, host: str) -> TenantDomain | None:
        for domain in self.saved:
            if domain.host == host:
                return domain
        return None

    async def get_api_host_by_tenant_id(self, tenant_id: UUID) -> str | None:
        return None

    async def exists_by_host(self, host: str) -> bool:
        return host in self._hosts


class FakeIdentityProvisioningService:
    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin:
        return ProvisionedTenantAdmin(
            user_id=uuid4(),
            user_email_id=uuid4(),
            user_status="active",
        )


class TestCreateTenantUseCase(unittest.IsolatedAsyncioTestCase):
    async def test_execute_creates_tenant_domain_and_user(self) -> None:
        uow = FakeUoW()
        tenants_repository = FakeTenantRepository()
        tenant_domains_repository = FakeTenantDomainRepository()
        use_case = CreateTenantUseCase(
            uow=uow,
            tenants_repository=tenants_repository,
            tenant_domains_repository=tenant_domains_repository,
            identity_provisioning_service=FakeIdentityProvisioningService(),
        )

        result = await use_case.execute(
            CreateTenantCommand(
                tenant_name="Acme",
                external_id="acme-ext",
                tenant_domain_host="Console.Acme.local:443",
                user_last_name="Doe",
                user_first_name="Jane",
                user_email="jane@example.com",
            )
        )

        self.assertTrue(uow.entered)
        self.assertTrue(uow.exited)
        self.assertEqual(uow.commits, 1)
        self.assertEqual(len(tenants_repository.saved), 1)
        self.assertEqual(len(tenant_domains_repository.saved), 1)
        self.assertEqual(tenant_domains_repository.saved[0].host, "console.acme.local")
        self.assertEqual(result.tenant_status, "active")
        self.assertEqual(result.user_status, "active")

    async def test_execute_raises_for_duplicate_tenant_name(self) -> None:
        uow = FakeUoW()
        tenants_repository = FakeTenantRepository()
        tenants_repository._names.add("Acme")
        use_case = CreateTenantUseCase(
            uow=uow,
            tenants_repository=tenants_repository,
            tenant_domains_repository=FakeTenantDomainRepository(),
            identity_provisioning_service=FakeIdentityProvisioningService(),
        )

        with self.assertRaises(TenantNameAlreadyExistsError):
            await use_case.execute(
                CreateTenantCommand(
                    tenant_name="Acme",
                    external_id="acme-ext",
                    tenant_domain_host="acme.local",
                    user_last_name="Doe",
                    user_first_name="Jane",
                    user_email="jane@example.com",
                )
            )

        self.assertTrue(uow.entered)
        self.assertTrue(uow.exited)
        self.assertEqual(uow.commits, 0)

    async def test_execute_raises_for_empty_host(self) -> None:
        uow = FakeUoW()
        use_case = CreateTenantUseCase(
            uow=uow,
            tenants_repository=FakeTenantRepository(),
            tenant_domains_repository=FakeTenantDomainRepository(),
            identity_provisioning_service=FakeIdentityProvisioningService(),
        )

        with self.assertRaises(InvalidTenantDomainHostError):
            await use_case.execute(
                CreateTenantCommand(
                    tenant_name="Acme",
                    external_id="acme-ext",
                    tenant_domain_host="   ",
                    user_last_name="Doe",
                    user_first_name="Jane",
                    user_email="jane@example.com",
                )
            )

        self.assertTrue(uow.entered)
        self.assertTrue(uow.exited)
        self.assertEqual(uow.commits, 0)
