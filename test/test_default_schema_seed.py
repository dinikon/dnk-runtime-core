from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.application.migration.operations import (
    CreateSchemaOperation,
)
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.postgres_schema_plan_service import (
    PostgresSchemaPlanService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)
from src.modules.schema_registry.infrastructure.tenancy_schema_bootstrap_adapter import (
    SchemaRegistryTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContext,
)


class DefaultSchemaSeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_seed_is_empty_runtime_manifest(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        self.assertEqual(seed.code, "runtime")
        self.assertEqual(seed.label, "Runtime")
        self.assertEqual(seed.objects, ())

    async def test_default_seed_creates_only_tenant_schema(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )
        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )
        plan = PostgresSchemaPlanService(
            field_type_catalog=FieldTypeCatalog(),
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        ).build_create_plan(schema_name="dnk_test", seed=seed)

        self.assertEqual(len(plan.operations), 1)
        self.assertIsInstance(plan.operations[0], CreateSchemaOperation)
        self.assertEqual(plan.operations[0].schema_name, "dnk_test")

    async def test_tenant_bootstrap_writes_empty_runtime_metadata(self) -> None:
        applied_operations = ()
        metadata_seed = None

        class PostgresSchemaServiceStub:
            async def ensure_schema_absent(self, *, schema_name: str) -> None:
                self.schema_name = schema_name

            async def apply_plan(self, *, plan) -> None:
                nonlocal applied_operations
                applied_operations = plan.operations

        class MetadataWriteServiceStub:
            async def create_from_seed(
                self,
                *,
                tenant_id,
                schema_name: str,
                seed,
            ) -> None:
                nonlocal metadata_seed
                metadata_seed = seed

        use_case = CreateSchemaUseCase(
            schema_seed_service=SchemaSeedService(
                PythonModuleSeedReader(),
                FieldTypeCatalog(),
            ),
            schema_plan_service=PostgresSchemaPlanService(
                field_type_catalog=FieldTypeCatalog(),
                postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
            ),
            postgres_schema_service=PostgresSchemaServiceStub(),
            schema_registry_metadata_write_service=MetadataWriteServiceStub(),
        )
        adapter = SchemaRegistryTenantSchemaBootstrapAdapter(use_case)

        await adapter.bootstrap(
            TenantSchemaBootstrapContext(
                tenant_id=uuid4(),
                schema_name="dnk_test",
                seed_path="src.modules.schema_registry.seed.schema_seed",
            )
        )

        self.assertEqual(len(applied_operations), 1)
        self.assertIsInstance(applied_operations[0], CreateSchemaOperation)
        self.assertEqual(metadata_seed.code, "runtime")
        self.assertEqual(metadata_seed.objects, ())


if __name__ == "__main__":
    unittest.main()
