from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.runtime_schema.domain.field.configuration import (
    FieldOption,
    FullNameFieldSettings,
    RelationFieldSettings,
    SelectFieldOptions,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldName, FieldTypeVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import ObjectNameVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.ddl_diff_engine import DdlDiffEngine
from src.modules.runtime_schema.infrastructure.ddl_models import (
    ColumnSpec,
    DdlDiff,
    IndexToCreate,
    IndexSpec,
    SchemaSnapshot,
    TableSpec,
    TableToCreate,
)
from src.modules.runtime_schema.infrastructure.ddl_plan_builder import DdlPlanBuilder
from src.modules.runtime_schema.infrastructure.field_layout_compiler import FieldLayoutCompiler
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def _tenant_id() -> EntityIdVO:
    return EntityIdVO.from_value(uuid4())


def _source_id() -> DataSourceIdVO:
    return DataSourceIdVO.from_value(uuid4())


class TestLayoutDiffPlan(unittest.TestCase):
    def test_field_layout_compiler_builds_table_snapshot(self) -> None:
        tenant_id = _tenant_id()
        source_id = _source_id()
        object_entity = ObjectMetadataEntity.create(
            tenant_id=tenant_id,
            data_source_id=source_id,
            object_name=ObjectNameVO(name_singular="lead", name_plural="leads"),
            is_system=True,
            is_custom=False,
        )
        field_title = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_entity.id,
            field_type=FieldTypeVO.STRING,
            field_name=FieldName("title"),
            label="Title",
            is_system=True,
            is_custom=False,
            is_nullable=False,
            is_index=True,
        )
        field_owner = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_entity.id,
            field_type=FieldTypeVO.RELATION,
            field_name=FieldName("owner_id"),
            label="Owner",
            is_system=True,
            is_custom=False,
            is_nullable=True,
            settings=RelationFieldSettings(max_links=1),
            relation_target_object_id=object_entity.id,
        )
        field_person_name = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_entity.id,
            field_type=FieldTypeVO.FULL_NAME,
            field_name=FieldName("name"),
            label="Name",
            is_system=True,
            is_custom=False,
            is_nullable=False,
            settings=FullNameFieldSettings(
                require_last_name=False,
                require_middle_name=False,
                require_first_name=True,
            ),
        )
        snapshot = FieldLayoutCompiler().compile_layout(
            objects=[object_entity],
            fields=[field_title, field_owner, field_person_name],
        )
        self.assertIn("leads", snapshot.tables)
        lead_table = snapshot.tables["leads"]
        column_names = [column.name for column in lead_table.columns]
        self.assertIn("id", column_names)
        self.assertIn("title", column_names)
        self.assertIn("owner_id", column_names)
        self.assertIn("name_last_name", column_names)
        self.assertIn("name_middle_name", column_names)
        self.assertIn("name_first_name", column_names)
        self.assertIn("created_at", column_names)
        self.assertIn("updated_at", column_names)
        self.assertTrue(any(index.columns == ("title",) for index in lead_table.indexes))
        columns_by_name = {column.name: column for column in lead_table.columns}
        self.assertTrue(columns_by_name["name_last_name"].nullable)
        self.assertTrue(columns_by_name["name_middle_name"].nullable)
        self.assertFalse(columns_by_name["name_first_name"].nullable)
        self.assertEqual(columns_by_name["owner_id"].references_table, "leads")
        self.assertEqual(columns_by_name["owner_id"].references_column, "id")

    def test_ddl_diff_engine(self) -> None:
        expected = SchemaSnapshot(
            tables={
                "items": TableSpec(
                    name="items",
                    columns=(
                        ColumnSpec(name="id", sql_type="uuid", nullable=False, is_primary_key=True),
                        ColumnSpec(name="title", sql_type="varchar(255)", nullable=False),
                    ),
                    indexes=(
                        IndexSpec(name="ix_items_title", columns=("title",), unique=False),
                    ),
                )
            }
        )
        actual = SchemaSnapshot.empty()
        diff = DdlDiffEngine().diff(expected=expected, actual=actual, allow_destructive=False)
        self.assertEqual(len(diff.tables_to_create), 1)
        self.assertEqual(len(diff.indexes_to_create), 1)

        actual_with_extra = SchemaSnapshot(
            tables={
                "items": TableSpec(
                    name="items",
                    columns=(
                        ColumnSpec(name="id", sql_type="uuid", nullable=False, is_primary_key=True),
                        ColumnSpec(name="title", sql_type="varchar(255)", nullable=False),
                        ColumnSpec(name="legacy", sql_type="text", nullable=True),
                    ),
                    indexes=tuple(),
                ),
                "legacy_table": TableSpec(name="legacy_table", columns=tuple(), indexes=tuple()),
            }
        )
        destructive_diff = DdlDiffEngine().diff(
            expected=expected,
            actual=actual_with_extra,
            allow_destructive=True,
        )
        self.assertEqual(len(destructive_diff.columns_to_drop), 1)
        self.assertEqual(len(destructive_diff.tables_to_drop), 1)

    def test_field_layout_compiler_adds_entity_owner_composite_index(self) -> None:
        tenant_id = _tenant_id()
        source_id = _source_id()
        object_entity = ObjectMetadataEntity.create(
            tenant_id=tenant_id,
            data_source_id=source_id,
            object_name=ObjectNameVO(
                name_singular="contact_point",
                name_plural="contact_points",
            ),
            is_system=True,
            is_custom=False,
        )
        entity_name_field = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_entity.id,
            field_type=FieldTypeVO.SELECT,
            field_name=FieldName("entity_name"),
            label="Entity Name",
            is_system=True,
            is_custom=False,
            is_nullable=False,
            options=SelectFieldOptions(
                items=(
                    FieldOption(code="lead", label="Lead"),
                    FieldOption(code="contact", label="Contact"),
                )
            ),
        )
        entity_uuid_field = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_entity.id,
            field_type=FieldTypeVO.UUID,
            field_name=FieldName("entity_uuid"),
            label="Entity UUID",
            is_system=True,
            is_custom=False,
            is_nullable=False,
        )
        snapshot = FieldLayoutCompiler().compile_layout(
            objects=[object_entity],
            fields=[entity_name_field, entity_uuid_field],
        )
        indexes = snapshot.tables["contact_points"].indexes
        self.assertTrue(
            any(index.columns == ("entity_name", "entity_uuid") for index in indexes)
        )

    def test_ddl_plan_builder_for_sqlite_and_postgresql(self) -> None:
        diff = DdlDiff(
            tables_to_create=(
                TableToCreate(
                    table=TableSpec(
                        name="items",
                        columns=(
                            ColumnSpec(
                                name="id",
                                sql_type="uuid",
                                nullable=False,
                                is_primary_key=True,
                            ),
                            ColumnSpec(name="title", sql_type="varchar(255)", nullable=False),
                            ColumnSpec(name="is_active", sql_type="boolean", nullable=False),
                            ColumnSpec(name="payload", sql_type="json", nullable=True),
                        ),
                        indexes=(IndexSpec(name="ix_items_title", columns=("title",), unique=False),),
                    )
                ),
            ),
            indexes_to_create=(
                IndexToCreate(
                    table_name="items",
                    index=IndexSpec(name="ix_items_title", columns=("title",), unique=False),
                ),
            ),
        )
        sqlite_plan = DdlPlanBuilder(dialect_name="sqlite").build(schema="tenant", diff=diff)
        self.assertGreaterEqual(len(sqlite_plan.operations), 2)
        self.assertTrue(any("tenant__items" in op.sql for op in sqlite_plan.operations))

        pg_builder = DdlPlanBuilder(dialect_name="postgresql")
        pg_plan = pg_builder.build(schema="tenant", diff=diff)
        self.assertTrue(any('"tenant"."items"' in op.sql for op in pg_plan.operations))

        rename_op = pg_builder.build_rename_table_operation(
            schema="tenant",
            old_table_name="old_items",
            new_table_name="items",
        )
        self.assertIn("RENAME TO", rename_op.sql)


if __name__ == "__main__":
    unittest.main()
