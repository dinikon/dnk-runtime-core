from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.schema_registry.application.command.diff_schema_command import (
    DiffSchemaCommand,
)
from src.modules.schema_registry.application.use_case.diff_schema_use_case import (
    DiffSchemaUseCase,
)
from src.modules.schema_registry.domain.migration.plan import MigrationPlan
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class DiffSchemaUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrates_services_without_uow_access(self) -> None:
        calls: list[str] = []
        tenant_id = uuid4()
        seed = SchemaSeed(version=None, code="crm", label="CRM", objects=())
        plan = MigrationPlan()

        class DataSource:
            class SchemaName:
                value = "dnk_crm"

            schema_name = SchemaName()

        class SeedService:
            async def load(self, *, seed_path: str) -> SchemaSeed:
                calls.append(f"seed:{seed_path}")
                return seed

        class DataSourceServiceStub:
            async def get_required_by_tenant(self, *, tenant_id):
                calls.append(f"datasource:{tenant_id}")
                return DataSource()

        class DiffService:
            def build_diff_plan(
                self,
                *,
                schema_name: str,
                seed: SchemaSeed,
                actual_schema,
            ) -> MigrationPlan:
                calls.append(f"plan:{schema_name}:{actual_schema['schema_name']}")
                return plan

        class PostgresService:
            async def inspect_schema(self, *, schema_name: str):
                calls.append(f"inspect:{schema_name}")
                return {"schema_name": schema_name}

            async def apply_plan(self, *, plan: MigrationPlan) -> None:
                calls.append(f"apply:{len(plan.operations)}")

        class MetadataService:
            async def replace_from_seed(self, *, tenant_id, seed: SchemaSeed) -> None:
                calls.append(f"metadata:{tenant_id}:{seed.code}")

        use_case = DiffSchemaUseCase(
            schema_seed_service=SeedService(),
            data_source_service=DataSourceServiceStub(),
            schema_diff_service=DiffService(),
            postgres_schema_service=PostgresService(),
            schema_registry_metadata_service=MetadataService(),
        )

        await use_case.execute(
            DiffSchemaCommand(
                tenant_id=tenant_id,
                seed_path="seed.module",
            )
        )

        self.assertEqual(
            calls,
            [
                "seed:seed.module",
                f"datasource:{tenant_id}",
                "inspect:dnk_crm",
                "plan:dnk_crm:dnk_crm",
                "apply:0",
                f"metadata:{tenant_id}:crm",
            ],
        )
