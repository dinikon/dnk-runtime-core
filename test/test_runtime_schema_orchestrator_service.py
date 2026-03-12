from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import select

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.dto import (
    BootstrapTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
    DeleteFieldCommandDTO,
    UpdateFieldCommandDTO,
)
from src.modules.runtime_schema.application.object_definition.dto import (
    CreateObjectCommandDTO,
    DeleteObjectCommandDTO,
    UpdateObjectCommandDTO,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.ddl_models import (
    DdlOperation,
    DdlOperationKind,
    DdlPlan,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.runtime_schema.infrastructure.persistence.models import (
    SchemaMigrationJournalModel,
)
from src.modules.shared.domain.errors import ValidationError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.runtime_schema_test_utils import sqlite_session


class TestDdlOrchestratorService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tenant_id = uuid4()
        self.data_source_id = uuid4()
        self.schema = "tenant_test"

    async def test_sync_and_bootstrap_are_idempotent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.yaml"
            manifest_path.write_text(
                """
version: "1.0.0"
objects:
  - key: "note"
    name: {singular: "note", plural: "notes"}
    label: {singular: "Note", plural: "Notes"}
    is_system: true
    is_custom: false
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
        is_system: true
        is_custom: false
      - name: "title"
        type: "string"
        label: "Title"
        is_system: true
        is_custom: false
        is_nullable: false
        is_index: true
""".strip(),
                encoding="utf-8",
            )

            async with sqlite_session() as session:
                orchestrator = build_ddl_orchestrator(
                    session=session,
                    manifest_path=manifest_path,
                )
                first = await orchestrator.sync_tenant_system_schema(
                    SyncTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )
                second = await orchestrator.sync_tenant_system_schema(
                    SyncTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )
                self.assertGreater(first.applied_operations, 0)
                self.assertEqual(second.applied_operations, 0)

                bootstrap_result = await orchestrator.bootstrap_tenant_system_schema(
                    BootstrapTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )
                self.assertEqual(bootstrap_result.applied_operations, 0)

    async def test_object_and_field_crud(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.yaml"
            manifest_path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    is_system: true
    is_custom: false
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
        is_system: true
        is_custom: false
""".strip(),
                encoding="utf-8",
            )

            async with sqlite_session() as session:
                orchestrator = build_ddl_orchestrator(
                    session=session,
                    manifest_path=manifest_path,
                )
                await orchestrator.sync_tenant_system_schema(
                    SyncTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )

                created_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="custom_note",
                        object_name_plural="custom_notes",
                        is_system=False,
                        is_custom=True,
                    )
                )
                self.assertEqual(created_object.object_name_singular, "custom_note")

                updated_object = await orchestrator.update_object_definition(
                    UpdateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=created_object.id,
                        schema=self.schema,
                        description="Updated",
                        is_active=True,
                    )
                )
                self.assertEqual(updated_object.description, "Updated")

                created_field = await orchestrator.create_field_definition(
                    CreateFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=created_object.id,
                        schema=self.schema,
                        field_type="string",
                        field_name="title",
                        label="Title",
                        is_system=False,
                        is_custom=True,
                        is_nullable=False,
                        is_index=True,
                    )
                )
                self.assertEqual(created_field.field_name, "title")

                updated_field = await orchestrator.update_field_definition(
                    UpdateFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        field_id=created_field.id,
                        schema=self.schema,
                        label="Subject",
                        is_searchable=True,
                    )
                )
                self.assertEqual(updated_field.label, "Subject")

                await orchestrator.delete_field_definition(
                    DeleteFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        field_id=created_field.id,
                        schema=self.schema,
                        allow_destructive=False,
                    )
                )
                await orchestrator.delete_object_definition(
                    DeleteObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=created_object.id,
                        schema=self.schema,
                        allow_destructive=False,
                    )
                )

    async def test_orchestrator_negative_paths(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.yaml"
            manifest_path.write_text(
                """
version: "1.0.0"
objects:
  - key: "lead"
    name: {singular: "lead", plural: "leads"}
    label: {singular: "Lead", plural: "Leads"}
    is_system: true
    is_custom: false
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
        is_system: true
        is_custom: false
""".strip(),
                encoding="utf-8",
            )

            async with sqlite_session() as session:
                orchestrator = build_ddl_orchestrator(
                    session=session,
                    manifest_path=manifest_path,
                )
                await orchestrator.sync_tenant_system_schema(
                    SyncTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )

                created_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="custom_task",
                        object_name_plural="custom_tasks",
                        is_system=False,
                        is_custom=True,
                    )
                )

                with self.assertRaises(ValidationError):
                    await orchestrator.update_object_definition(
                        UpdateObjectCommandDTO(
                            tenant_id=self.tenant_id,
                            object_id=created_object.id,
                            schema=self.schema,
                            object_name_singular="custom_task_new",
                            allow_ddl_rename=False,
                        )
                    )

                created_field = await orchestrator.create_field_definition(
                    CreateFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=created_object.id,
                        schema=self.schema,
                        field_type="string",
                        field_name="name",
                        label="Name",
                        is_system=False,
                        is_custom=True,
                    )
                )

                with self.assertRaises(ValidationError):
                    await orchestrator.update_field_definition(
                        UpdateFieldCommandDTO(
                            tenant_id=self.tenant_id,
                            field_id=created_field.id,
                            schema=self.schema,
                            options={"items": [{"code": "x", "label": "X"}]},
                        )
                    )

    async def test_object_rename_with_allow_ddl_rename(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.yaml"
            manifest_path.write_text(
                """
version: "1.0.0"
objects:
  - key: "seed"
    name: {singular: "seed", plural: "seeds"}
    label: {singular: "Seed", plural: "Seeds"}
    is_system: true
    is_custom: false
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
        is_system: true
        is_custom: false
""".strip(),
                encoding="utf-8",
            )
            async with sqlite_session() as session:
                orchestrator = build_ddl_orchestrator(
                    session=session,
                    manifest_path=manifest_path,
                )
                await orchestrator.sync_tenant_system_schema(
                    SyncTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )
                created_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="legacy_task",
                        object_name_plural="legacy_tasks",
                        is_system=False,
                        is_custom=True,
                    )
                )
                updated_object = await orchestrator.update_object_definition(
                    UpdateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=created_object.id,
                        schema=self.schema,
                        object_name_singular="task",
                        object_name_plural="tasks",
                        object_label_singular="Task",
                        object_label_plural="Tasks",
                        icon="icon-task",
                        shortcut="T",
                        is_ui_read_only=True,
                        duplicate_criteria={"code": "task_code"},
                        allow_ddl_rename=True,
                    )
                )
                self.assertEqual(updated_object.object_name_singular, "task")
                self.assertEqual(updated_object.object_name_plural, "tasks")
                self.assertEqual(updated_object.object_label_singular, "Task")

    async def test_relation_target_validation_and_sync_schema_validation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.yaml"
            manifest_path.write_text(
                """
version: "1.0.0"
objects:
  - key: "seed"
    name: {singular: "seed", plural: "seeds"}
    label: {singular: "Seed", plural: "Seeds"}
    is_system: true
    is_custom: false
    fields:
      - name: "id"
        type: "uuid"
        label: "ID"
        is_system: true
        is_custom: false
""".strip(),
                encoding="utf-8",
            )
            async with sqlite_session() as session:
                orchestrator = build_ddl_orchestrator(
                    session=session,
                    manifest_path=manifest_path,
                )
                with self.assertRaises(ValidationError):
                    await orchestrator.sync_tenant_system_schema(
                        SyncTenantSystemSchemaCommandDTO(
                            tenant_id=self.tenant_id,
                            data_source_id=self.data_source_id,
                            schema=None,  # type: ignore[arg-type]
                        )
                    )

                await orchestrator.sync_tenant_system_schema(
                    SyncTenantSystemSchemaCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                    )
                )
                source_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="ticket",
                        object_name_plural="tickets",
                        is_system=False,
                        is_custom=True,
                    )
                )
                target_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="account",
                        object_name_plural="accounts",
                        is_system=False,
                        is_custom=True,
                    )
                )
                alternate_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="profile",
                        object_name_plural="profiles",
                        is_system=False,
                        is_custom=True,
                    )
                )
                target_field = await orchestrator.create_field_definition(
                    CreateFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=target_object.id,
                        schema=self.schema,
                        field_type="uuid",
                        field_name="external_id",
                        label="External Id",
                        is_system=False,
                        is_custom=True,
                    )
                )
                alternate_field = await orchestrator.create_field_definition(
                    CreateFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=alternate_object.id,
                        schema=self.schema,
                        field_type="uuid",
                        field_name="external_id",
                        label="External Id",
                        is_system=False,
                        is_custom=True,
                    )
                )

                with self.assertRaises(ValidationError):
                    await orchestrator.create_field_definition(
                        CreateFieldCommandDTO(
                            tenant_id=self.tenant_id,
                            object_id=source_object.id,
                            schema=self.schema,
                            field_type="relation",
                            field_name="missing_object",
                            label="Missing Object",
                            is_system=False,
                            is_custom=True,
                            relation_target_object_id=uuid4(),
                        )
                    )
                with self.assertRaises(ValidationError):
                    await orchestrator.create_field_definition(
                        CreateFieldCommandDTO(
                            tenant_id=self.tenant_id,
                            object_id=source_object.id,
                            schema=self.schema,
                            field_type="relation",
                            field_name="missing_field",
                            label="Missing Field",
                            is_system=False,
                            is_custom=True,
                            relation_target_object_id=target_object.id,
                            relation_target_field_id=uuid4(),
                        )
                    )
                with self.assertRaises(ValidationError):
                    await orchestrator.create_field_definition(
                        CreateFieldCommandDTO(
                            tenant_id=self.tenant_id,
                            object_id=source_object.id,
                            schema=self.schema,
                            field_type="relation",
                            field_name="mismatch_field",
                            label="Mismatch Field",
                            is_system=False,
                            is_custom=True,
                            relation_target_object_id=target_object.id,
                            relation_target_field_id=alternate_field.id,
                        )
                    )

                other_tenant_id = uuid4()
                foreign_object = await orchestrator.create_object_definition(
                    CreateObjectCommandDTO(
                        tenant_id=other_tenant_id,
                        data_source_id=self.data_source_id,
                        schema=self.schema,
                        object_name_singular="foreign_account",
                        object_name_plural="foreign_accounts",
                        is_system=False,
                        is_custom=True,
                    )
                )
                with self.assertRaises(ValidationError):
                    await orchestrator.create_field_definition(
                        CreateFieldCommandDTO(
                            tenant_id=self.tenant_id,
                            object_id=source_object.id,
                            schema=self.schema,
                            field_type="relation",
                            field_name="foreign_object",
                            label="Foreign Object",
                            is_system=False,
                            is_custom=True,
                            relation_target_object_id=foreign_object.id,
                        )
                    )

                relation_field = await orchestrator.create_field_definition(
                    CreateFieldCommandDTO(
                        tenant_id=self.tenant_id,
                        object_id=source_object.id,
                        schema=self.schema,
                        field_type="relation",
                        field_name="account_id",
                        label="Account",
                        is_system=False,
                        is_custom=True,
                        relation_target_object_id=target_object.id,
                        relation_target_field_id=target_field.id,
                    )
                )
                self.assertEqual(relation_field.field_name, "account_id")
                with self.assertRaises(ValidationError):
                    await orchestrator.update_field_definition(
                        UpdateFieldCommandDTO(
                            tenant_id=self.tenant_id,
                            field_id=relation_field.id,
                            schema=self.schema,
                            relation_target_object_id=target_object.id,
                            relation_target_field_id=alternate_field.id,
                        )
                    )

    async def test_execute_ddl_plan_failure_writes_failed_journal(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.yaml"
            manifest_path.write_text("version: '1.0.0'\nobjects: []", encoding="utf-8")
            async with sqlite_session() as session:
                orchestrator = build_ddl_orchestrator(
                    session=session,
                    manifest_path=manifest_path,
                )
                with self.assertRaises(ValidationError):
                    await orchestrator._execute_ddl_plan(  # noqa: SLF001
                        tenant_id=EntityIdVO.from_value(uuid4()),
                        data_source_id=DataSourceIdVO.from_value(uuid4()),
                        schema=self.schema,
                        plan=DdlPlan(
                            operations=(
                                DdlOperation(
                                    key="bad_sql",
                                    kind=DdlOperationKind.CREATE_TABLE,
                                    sql="THIS IS INVALID SQL",
                                ),
                            )
                        ),
                    )
                entries = (
                    await session.scalars(select(SchemaMigrationJournalModel))
                ).all()
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0].status, "FAILED")


if __name__ == "__main__":
    unittest.main()
