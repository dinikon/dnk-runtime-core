from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.infrastructure.tenancy_schema_bootstrap_adapter import (
    SchemaRegistryTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContext,
    TenantSchemaBootstrapContextFactory,
)


class TenantSchemaBootstrapBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def test_context_factory_builds_tenancy_owned_bootstrap_context(self) -> None:
        tenant_id = uuid4()
        factory = TenantSchemaBootstrapContextFactory(
            schema_prefix="dnk_",
            default_seed_path="seed.module",
        )

        context = factory.build(tenant_id=tenant_id)

        self.assertEqual(context.tenant_id, tenant_id)
        self.assertEqual(context.schema_name, f"dnk_{tenant_id.hex}")
        self.assertEqual(context.seed_path, "seed.module")

    async def test_adapter_translates_context_to_create_schema_command(self) -> None:
        recorded_command = None

        class CreateSchemaUseCaseStub:
            async def execute(self, command):
                nonlocal recorded_command
                recorded_command = command

        adapter = SchemaRegistryTenantSchemaBootstrapAdapter(CreateSchemaUseCaseStub())
        context = TenantSchemaBootstrapContext(
            tenant_id=uuid4(),
            schema_name="dnk_example",
            seed_path="seed.module",
        )

        await adapter.bootstrap(context=context)

        self.assertEqual(recorded_command.tenant_id, context.tenant_id)
        self.assertEqual(recorded_command.schema_name, context.schema_name)
        self.assertEqual(recorded_command.seed_path, context.seed_path)
