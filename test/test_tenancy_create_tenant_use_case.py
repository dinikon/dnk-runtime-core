from __future__ import annotations

import unittest
from dataclasses import dataclass
from uuid import uuid4

from src.modules.tenancy.application.commands import CreateTenantCommand
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.use_cases.create_tenant import CreateTenantUseCase
from src.modules.tenancy.domain.services import TenantOnboardingDraft
from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.value_objects import (
    TenantDomainKind,
    TenantDomainStatus,
    TenantDomainTlsMode,
    TenantDomainVerificationStatus,
    TenantServiceType,
    TenantStatus,
)


class CreateTenantUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstraps_schema_with_hex_schema_name(self) -> None:
        tenant = Tenant.create(name="Tenant", external_id="tenant-1")
        tenant_domain = TenantDomain.create_primary_console_domain(
            tenant_id=tenant.id,
            host="tenant.example.com",
        )
        created_user_id = uuid4()
        created_user_email_id = uuid4()
        recorded_context = None

        class TenantOnboardingServiceStub:

            async def create_tenant_with_primary_domain(
                self, **kwargs
            ) -> TenantOnboardingDraft:
                return TenantOnboardingDraft(
                    tenant=tenant,
                    tenant_domain=tenant_domain,
                )

        class IdentityProvisioningServiceStub:
            async def create_tenant_admin(self, **kwargs):
                return type(
                    "Provisioned",
                    (),
                    {
                        "user_id": created_user_id,
                        "user_email_id": created_user_email_id,
                        "user_status": "active",
                    },
                )()

        class TenantSchemaBootstrapPortStub:
            async def bootstrap(self, *, context):
                nonlocal recorded_context
                recorded_context = context

        use_case = CreateTenantUseCase(
            tenant_onboarding_service=TenantOnboardingServiceStub(),
            identity_provisioning_service=IdentityProvisioningServiceStub(),
            tenant_schema_bootstrap_context_factory=TenantSchemaBootstrapContextFactory(
                schema_prefix="dnk_",
                default_seed_path="seed.module",
            ),
            tenant_schema_bootstrap_port=TenantSchemaBootstrapPortStub(),
        )

        result = await use_case.execute(
            CreateTenantCommand(
                tenant_name="Tenant",
                external_id="tenant-1",
                tenant_domain_host="tenant.example.com",
                user_last_name="Doe",
                user_first_name="John",
                user_email="john@example.com",
            )
        )

        self.assertIsNotNone(recorded_context)
        self.assertEqual(
            recorded_context.schema_name,
            f"dnk_{tenant.id.hex}",
        )
        self.assertEqual(recorded_context.seed_path, "seed.module")
        self.assertEqual(result.tenant_id, tenant.id)
        self.assertEqual(result.user_id, created_user_id)
