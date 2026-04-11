from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AlterColumnDefaultOperation,
    AlterColumnNullableOperation,
    CreateIndexOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
    DropTableOperation,
)
from src.modules.schema_registry.application.migration.plan import MigrationPlan
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.infrastructure.postgres.tenant_schema_executor import (
    PostgresTenantSchemaExecutor,
)


class PostgresTenantSchemaExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_renders_sql_for_drop_and_add_operations(self) -> None:
        executed_sql: list[str] = []

        class Bind:
            class Dialect:
                name = "postgresql"

            dialect = Dialect()

        class SessionStub:
            def get_bind(self):
                return Bind()

            async def execute(self, statement) -> None:
                executed_sql.append(str(statement))

            async def flush(self) -> None:
                return None

        executor = PostgresTenantSchemaExecutor(
            SessionStub(),
            PostgresFieldCanonicalizer(),
        )
        plan = MigrationPlan(
            operations=[
                DropForeignKeyOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    constraint_name="contacts_company_fk",
                ),
                DropIndexOperation(
                    schema_name="dnk_crm",
                    index_name="contacts_last_name_idx",
                ),
                DropColumnOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    column_name="legacy_name",
                ),
                DropTableOperation(
                    schema_name="dnk_crm",
                    table_name="legacy_contacts",
                ),
                CreateTableOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                ),
                AddColumnOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    column_name="last_name",
                    sql_preset=SqlTypePresetEnum.TEXT,
                    is_nullable=False,
                    default_value="'unknown'",
                ),
                AlterColumnDefaultOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    column_name="id",
                    default_value="gen_random_uuid()",
                ),
                AlterColumnDefaultOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    column_name="legacy_name",
                    default_value=None,
                ),
                AlterColumnNullableOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    column_name="legacy_name",
                    is_nullable=True,
                ),
                CreateIndexOperation(
                    schema_name="dnk_crm",
                    table_name="contacts",
                    index_name="contacts_last_name_idx",
                    columns=("last_name",),
                    is_unique=False,
                ),
            ]
        )

        await executor.execute(plan=plan)

        self.assertEqual(
            executed_sql,
            [
                'ALTER TABLE "dnk_crm"."contacts" DROP CONSTRAINT "contacts_company_fk"',
                'DROP INDEX "dnk_crm"."contacts_last_name_idx"',
                'ALTER TABLE "dnk_crm"."contacts" DROP COLUMN "legacy_name"',
                'DROP TABLE "dnk_crm"."legacy_contacts"',
                'CREATE TABLE "dnk_crm"."contacts" ()',
                'ALTER TABLE "dnk_crm"."contacts" ADD COLUMN "last_name" text NOT NULL DEFAULT \'unknown\'',
                'ALTER TABLE "dnk_crm"."contacts" ALTER COLUMN "id" SET DEFAULT gen_random_uuid()',
                'ALTER TABLE "dnk_crm"."contacts" ALTER COLUMN "legacy_name" DROP DEFAULT',
                'ALTER TABLE "dnk_crm"."contacts" ALTER COLUMN "legacy_name" DROP NOT NULL',
                'CREATE INDEX "contacts_last_name_idx" ON "dnk_crm"."contacts" ("last_name")',
            ],
        )
