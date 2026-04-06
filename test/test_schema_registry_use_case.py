from __future__ import annotations

import unittest
from dataclasses import dataclass
from uuid import uuid4

from src.modules.schema_registry.application.command.create_schema_command import (
    CreateSchemaCommand,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.schema_registry.domain.migration.plan import MigrationPlan
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


@dataclass(frozen=True, slots=True)
class CallRecord:
    name: str


class CreateSchemaUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrates_services_in_order(self) -> None:
        calls: list[str] = []
        seed = SchemaSeed(version=None, code="crm", label="CRM", objects=())
        plan = MigrationPlan()

        class SeedService:
            async def load(self, *, seed_path: str) -> SchemaSeed:
                calls.append(f"seed:{seed_path}")
                return seed

        class DiffService:
            def build_create_plan(
                self, *, schema_name: str, seed: SchemaSeed
            ) -> MigrationPlan:
                calls.append(f"plan:{schema_name}:{seed.code}")
                return plan

        class PostgresService:
            async def ensure_schema_absent(self, *, schema_name: str) -> None:
                calls.append(f"ensure:{schema_name}")

            async def apply_plan(self, *, plan: MigrationPlan) -> None:
                calls.append(f"apply:{len(plan.operations)}")

        class MetadataService:
            async def create_from_seed(
                self, *, tenant_id, schema_name: str, seed: SchemaSeed
            ) -> None:
                calls.append(f"metadata:{tenant_id}:{schema_name}:{seed.code}")

        use_case = CreateSchemaUseCase(
            schema_seed_service=SeedService(),
            schema_diff_service=DiffService(),
            postgres_schema_service=PostgresService(),
            schema_registry_metadata_service=MetadataService(),
        )

        tenant_id = uuid4()
        await use_case.execute(
            CreateSchemaCommand(
                tenant_id=tenant_id,
                schema_name="dnk_schema",
                seed_path="seed.module",
            )
        )

        self.assertEqual(
            calls,
            [
                "seed:seed.module",
                "ensure:dnk_schema",
                "plan:dnk_schema:crm",
                "apply:0",
                f"metadata:{tenant_id}:dnk_schema:crm",
            ],
        )
