from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.runtime_schema.domain.field.configuration import (
    FieldOption,
    RelationFieldSettings,
    SelectDefaultValue,
    SelectFieldOptions,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldName, FieldTypeVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import ObjectNameVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.ddl_executor import (
    DdlExecutionError,
    SqlAlchemyDdlExecutor,
)
from src.modules.runtime_schema.infrastructure.ddl_models import (
    DdlOperation,
    DdlOperationKind,
    DdlPlan,
    MigrationJournalEntry,
    SchemaSnapshot,
)
from src.modules.runtime_schema.infrastructure.ddl_plan_builder import DdlPlanBuilder
from src.modules.runtime_schema.infrastructure.factory import (
    build_ddl_orchestrator,
    default_system_manifest_path,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
    SqlAlchemySchemaMigrationJournalRepository,
    SqlAlchemySchemaVersionRepository,
)
from src.modules.runtime_schema.infrastructure.schema_introspector import (
    SqlAlchemySchemaIntrospector,
)
from src.modules.runtime_schema.infrastructure.schema_lock import SqlAlchemySchemaLockService
from src.modules.runtime_schema.infrastructure.contracts import SchemaVersionEntry
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.runtime_schema_test_utils import sqlite_session


def _tenant_id() -> EntityIdVO:
    return EntityIdVO.from_value(uuid4())


def _source_id() -> DataSourceIdVO:
    return DataSourceIdVO.from_value(uuid4())


class TestSqlAlchemyInfrastructure(unittest.IsolatedAsyncioTestCase):
    async def test_ddl_executor_success_and_failure(self) -> None:
        async with sqlite_session() as session:
            executor = SqlAlchemyDdlExecutor(session)
            plan = DdlPlan(
                operations=(
                    DdlOperation(
                        key="create_table:test",
                        kind=DdlOperationKind.CREATE_TABLE,
                        sql='CREATE TABLE "tenant__ddl_test" ("id" TEXT PRIMARY KEY)',
                    ),
                )
            )
            report = await executor.execute(
                tenant_id=_tenant_id(),
                data_source_id=_source_id(),
                schema="tenant",
                plan=plan,
            )
            self.assertEqual(report.applied_operations, 1)
            self.assertEqual(report.journal_entries[0].status, "APPLIED")

            bad_plan = DdlPlan(
                operations=(
                    DdlOperation(
                        key="bad",
                        kind=DdlOperationKind.CREATE_TABLE,
                        sql="THIS IS INVALID SQL",
                    ),
                )
            )
            with self.assertRaises(DdlExecutionError) as ctx:
                await executor.execute(
                    tenant_id=_tenant_id(),
                    data_source_id=_source_id(),
                    schema="tenant",
                    plan=bad_plan,
                )
            self.assertEqual(len(ctx.exception.journal_entries), 1)
            self.assertEqual(ctx.exception.journal_entries[0].status, "FAILED")

    async def test_schema_introspector_sqlite(self) -> None:
        async with sqlite_session() as session:
            plan_builder = DdlPlanBuilder(dialect_name="sqlite")
            plan = DdlPlan(
                operations=(
                    DdlOperation(
                        key="create_table:test_items",
                        kind=DdlOperationKind.CREATE_TABLE,
                        sql='CREATE TABLE "tenant_a__items" ("id" TEXT PRIMARY KEY, "title" TEXT)',
                    ),
                    DdlOperation(
                        key="create_index:test_items_title",
                        kind=DdlOperationKind.CREATE_INDEX,
                        sql='CREATE INDEX IF NOT EXISTS "ix_tenant_a_items_title" ON "tenant_a__items" ("title")',
                    ),
                )
            )
            await SqlAlchemyDdlExecutor(session).execute(
                tenant_id=_tenant_id(),
                data_source_id=_source_id(),
                schema="tenant_a",
                plan=plan,
            )
            snapshot = await SqlAlchemySchemaIntrospector(session).introspect(schema="tenant_a")
            self.assertIsInstance(snapshot, SchemaSnapshot)
            self.assertIn("items", snapshot.tables)
            self.assertTrue(any(idx.columns == ("title",) for idx in snapshot.tables["items"].indexes))
            _ = plan_builder  # keeps plan-builder import exercised

    async def test_schema_lock_service_non_postgres(self) -> None:
        async with sqlite_session() as session:
            lock_service = SqlAlchemySchemaLockService(session)
            async with lock_service.lock(tenant_id=_tenant_id(), schema="tenant_a"):
                self.assertTrue(True)
            key = lock_service._lock_key(tenant_id=_tenant_id(), schema="tenant_a")
            self.assertIsInstance(key, int)

    async def test_object_and_field_repositories(self) -> None:
        async with sqlite_session() as session:
            tenant_id = _tenant_id()
            data_source_id = _source_id()
            object_repo = SqlAlchemyObjectMetadataRepository(session)
            field_repo = SqlAlchemyFieldMetadataRepository(session)

            object_entity = ObjectMetadataEntity.create(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                object_name=ObjectNameVO(name_singular="note", name_plural="notes"),
                is_system=False,
                is_custom=True,
                description="desc",
            )
            await object_repo.add(object_entity)

            loaded_object = await object_repo.get_by_id(object_id=object_entity.id)
            self.assertIsNotNone(loaded_object)
            self.assertEqual(loaded_object.object_name.name_singular, "note")

            field_entity = FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.SELECT,
                field_name=FieldName("status"),
                label="Status",
                is_system=False,
                is_custom=True,
                is_index=True,
                options=SelectFieldOptions(
                    items=(FieldOption(code="new", label="New"),),
                    allow_custom=False,
                ),
                default_value=SelectDefaultValue(code="new"),
            )
            await field_repo.add(field_entity)

            by_name = await field_repo.get_by_object_and_name(
                object_id=object_entity.id,
                field_name="status",
            )
            self.assertIsNotNone(by_name)
            self.assertEqual(by_name.field_name.value, "status")

            relation_object = ObjectMetadataEntity.create(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                object_name=ObjectNameVO(name_singular="account", name_plural="accounts"),
                is_system=False,
                is_custom=True,
            )
            await object_repo.add(relation_object)
            relation_target = FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=relation_object.id,
                field_type=FieldTypeVO.UUID,
                field_name=FieldName("owner_id"),
                label="Owner Id",
                is_system=False,
                is_custom=True,
            )
            await field_repo.add(relation_target)
            relation_field = FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.RELATION,
                field_name=FieldName("account_id"),
                label="Account",
                is_system=False,
                is_custom=True,
                settings=RelationFieldSettings(max_links=1),
                relation_target_object_id=relation_object.id,
                relation_target_field_id=relation_target.id,
            )
            await field_repo.add(relation_field)
            loaded_relation = await field_repo.get_by_id(field_id=relation_field.id)
            self.assertEqual(
                loaded_relation.relation_target_object_id,
                relation_object.id,
            )
            self.assertEqual(loaded_relation.relation_target_field_id, relation_target.id)

            list_by_object = await field_repo.list_by_object(object_id=object_entity.id)
            self.assertEqual(len(list_by_object), 2)
            list_by_tenant = await field_repo.list_by_tenant(tenant_id=tenant_id)
            self.assertEqual(len(list_by_tenant), 3)

            field_entity.label = "State"
            field_entity.touch()
            await field_repo.save(field_entity)
            updated = await field_repo.get_by_id(field_id=field_entity.id)
            self.assertEqual(updated.label, "State")

            await field_repo.delete(field_id=field_entity.id)
            self.assertIsNone(await field_repo.get_by_id(field_id=field_entity.id))
            await field_repo.delete(field_id=relation_field.id)
            await field_repo.delete(field_id=relation_target.id)

            await object_repo.delete(object_id=object_entity.id)
            self.assertIsNone(await object_repo.get_by_id(object_id=object_entity.id))
            await object_repo.delete(object_id=relation_object.id)
            self.assertIsNone(await object_repo.get_by_id(object_id=relation_object.id))

    async def test_schema_version_and_journal_repositories(self) -> None:
        async with sqlite_session() as session:
            tenant_id = _tenant_id()
            data_source_id = _source_id()
            version_repo = SqlAlchemySchemaVersionRepository(session)
            journal_repo = SqlAlchemySchemaMigrationJournalRepository(session)
            self.assertIsNone(await version_repo.get(tenant_id=tenant_id, schema="tenant_a"))

            entry = SchemaVersionEntry(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema="tenant_a",
                version="1.0.0",
                manifest_hash="hash_1",
                updated_at=MigrationJournalEntry.applied(
                    operation_key="x",
                    operation_sql="select 1",
                ).created_at,
            )
            await version_repo.upsert(entry)
            loaded = await version_repo.get(tenant_id=tenant_id, schema="tenant_a")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.version, "1.0.0")

            await journal_repo.add_entries(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema="tenant_a",
                entries=[
                    MigrationJournalEntry.applied(
                        operation_key="op_1",
                        operation_sql="SQL1",
                    )
                ],
            )

    async def test_factory_builds_orchestrator(self) -> None:
        async with sqlite_session() as session:
            orchestrator = build_ddl_orchestrator(session=session)
            self.assertEqual(type(orchestrator).__name__, "DdlOrchestratorService")
            self.assertTrue(default_system_manifest_path().name.endswith(".yaml"))


if __name__ == "__main__":
    unittest.main()
