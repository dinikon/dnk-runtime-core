from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant import (
    CreateTenantCommand,
    CreateTenantUseCase,
)
from src.modules.tenancy.domain.service import TenantOnboardingDraft
from src.modules.tenancy.domain.tenant import Tenant
from src.modules.tenancy.domain.tenant_domain import TenantDomain


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
        steps = []

        class TenantOnboardingServiceStub:
            async def create_tenant_with_primary_domain(
                self, **kwargs
            ) -> TenantOnboardingDraft:
                steps.append("tenant")
                return TenantOnboardingDraft(
                    tenant=tenant,
                    tenant_domain=tenant_domain,
                )

        class IdentityProvisioningServiceStub:
            async def create_tenant_admin(self, **kwargs):
                steps.append("admin")
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
                steps.append("schema")

        use_case = CreateTenantUseCase(
            tenant_onboarding_service=TenantOnboardingServiceStub(),
            identity_provisioning_service=IdentityProvisioningServiceStub(),
            tenant_schema_bootstrap_context_factory=TenantSchemaBootstrapContextFactory(
                schema_prefix="dnk_",
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

        self.assertEqual(steps, ["tenant", "schema", "admin"])
        self.assertIsNotNone(recorded_context)
        self.assertEqual(
            recorded_context.schema_name,
            f"dnk_{tenant.id.uuid.hex}",
        )
        self.assertEqual(result.tenant_id, tenant.id.uuid)
        self.assertEqual(result.user_id, created_user_id)
