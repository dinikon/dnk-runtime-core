from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.modules.runtime_schema.domain.field.configuration import (
    FieldOption,
    MultiSelectFieldOptions,
    RelationFieldSettings,
    SelectFieldOptions,
    StringFieldSettings,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldName, FieldTypeVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import ObjectNameVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.ddl_models import (
    ColumnSpec,
    ColumnToAdd,
    ColumnToDrop,
    DdlDiff,
    SchemaSnapshot,
    TableSpec,
    TableToDrop,
)
from src.modules.runtime_schema.infrastructure.ddl_plan_builder import DdlPlanBuilder
from src.modules.runtime_schema.infrastructure.field_layout_compiler import FieldLayoutCompiler
from src.modules.runtime_schema.infrastructure.schema_introspector import (
    SqlAlchemySchemaIntrospector,
)
from src.modules.runtime_schema.infrastructure.schema_lock import SqlAlchemySchemaLockService
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def _tenant_id() -> EntityIdVO:
    return EntityIdVO.from_value(uuid4())


def _source_id() -> DataSourceIdVO:
    return DataSourceIdVO.from_value(uuid4())


class _FakeSyncSession:
    def connection(self) -> object:
        return object()


class _FakeInspector:
    def get_table_names(self, schema: str | None = None) -> list[str]:
        if schema is None:
            return []
        return ["accounts"]

    @staticmethod
    def get_columns(table_name: str, schema: str | None = None) -> list[dict[str, object]]:
        assert table_name == "accounts"
        _ = schema
        return [
            {"name": "id", "type": "UUID", "nullable": False},
            {"name": "payload", "type": "JSONB", "nullable": True},
            {"name": "is_active", "type": "BOOLEAN", "nullable": True},
        ]

    @staticmethod
    def get_pk_constraint(
        table_name: str,
        schema: str | None = None,
    ) -> dict[str, list[str]]:
        assert table_name == "accounts"
        _ = schema
        return {"constrained_columns": ["id"]}

    @staticmethod
    def get_indexes(
        table_name: str,
        schema: str | None = None,
    ) -> list[dict[str, object]]:
        assert table_name == "accounts"
        _ = schema
        return [
            {"column_names": [None], "unique": False},
            {"column_names": ["id"], "unique": True},
        ]


class TestInfraExtendedComponents(unittest.TestCase):
    def test_field_layout_compiler_covers_field_types(self) -> None:
        tenant_id = _tenant_id()
        data_source_id = _source_id()
        object_entity = ObjectMetadataEntity.create(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            object_name=ObjectNameVO(name_singular="contact", name_plural="contacts"),
        )
        inactive_object = ObjectMetadataEntity.create(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            object_name=ObjectNameVO(name_singular="archive", name_plural="archives"),
        )

        fields = [
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.UUID,
                field_name=FieldName("id"),
                label="Id",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("title"),
                label="Title",
                settings=StringFieldSettings(max_length=40),
                is_unique=True,
                is_index=True,
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.INTEGER,
                field_name=FieldName("priority"),
                label="Priority",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.BOOLEAN,
                field_name=FieldName("is_active"),
                label="Active",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.DATE_TIME,
                field_name=FieldName("planned_at"),
                label="Planned At",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.JSON,
                field_name=FieldName("payload"),
                label="Payload",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.ARRAY,
                field_name=FieldName("items"),
                label="Items",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.MULTI_SELECT,
                field_name=FieldName("tags"),
                label="Tags",
                options=MultiSelectFieldOptions(items=(FieldOption(code="a", label="A"),)),
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.SELECT,
                field_name=FieldName("status"),
                label="Status",
                options=SelectFieldOptions(items=(FieldOption(code="new", label="New"),)),
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.ACTOR,
                field_name=FieldName("owner_id"),
                label="Owner",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.ADDRESS,
                field_name=FieldName("address"),
                label="Address",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.FULL_NAME,
                field_name=FieldName("person_name"),
                label="Person Name",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.CURRENCY,
                field_name=FieldName("amount"),
                label="Amount",
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.RELATION,
                field_name=FieldName("account_links"),
                label="Account Links",
                settings=RelationFieldSettings(max_links=2),
                relation_target_object_id=object_entity.id,
            ),
            FieldMetadataEntity.create(
                tenant_id=tenant_id,
                object_metadata_id=object_entity.id,
                field_type=FieldTypeVO.STRING,
                field_name=FieldName("inactive_note"),
                label="Inactive Note",
            ),
        ]

        snapshot = FieldLayoutCompiler().compile_layout(
            objects=[object_entity, inactive_object],
            fields=fields,
        )
        self.assertIn("archives", snapshot.tables)
        self.assertIn("contacts", snapshot.tables)
        table = snapshot.tables["contacts"]
        column_names = {column.name for column in table.columns}
        self.assertIn("id", column_names)
        self.assertIn("priority", column_names)
        self.assertIn("is_active", column_names)
        self.assertIn("planned_at", column_names)
        self.assertIn("payload", column_names)
        self.assertIn("title", column_names)
        self.assertIn("address_country", column_names)
        self.assertIn("person_name_first_name", column_names)
        self.assertIn("amount_currency", column_names)
        self.assertNotIn("account_links", column_names)
        self.assertIn("inactive_note", column_names)
        self.assertTrue(any(index.unique for index in table.indexes))

    def test_ddl_plan_builder_destructive_and_references(self) -> None:
        diff = DdlDiff(
            columns_to_add=(
                ColumnToAdd(
                    table_name="orders",
                    column=ColumnSpec(
                        name="owner_id",
                        sql_type="uuid",
                        nullable=True,
                        references_table="users",
                        references_column="id",
                        on_delete="cascade",
                    ),
                ),
            ),
            columns_to_drop=(ColumnToDrop(table_name="orders", column_name="legacy"),),
            tables_to_drop=(TableToDrop(table_name="legacy_orders"),),
        )

        sqlite_builder = DdlPlanBuilder(dialect_name="sqlite")
        sqlite_plan = sqlite_builder.build(schema="tenant", diff=diff)
        self.assertFalse(any("DROP COLUMN" in operation.sql for operation in sqlite_plan.operations))
        self.assertTrue(any("DROP TABLE IF EXISTS" in operation.sql for operation in sqlite_plan.operations))

        pg_builder = DdlPlanBuilder(dialect_name="postgresql")
        pg_plan = pg_builder.build(schema="tenant", diff=diff)
        self.assertTrue(any("DROP COLUMN" in operation.sql for operation in pg_plan.operations))
        self.assertTrue(
            any(
                'REFERENCES "tenant"."users"("id") ON DELETE CASCADE' in operation.sql
                for operation in pg_plan.operations
            )
        )
        self.assertEqual(pg_builder._map_sql_type("timestamp_tz"), "TIMESTAMP WITH TIME ZONE")
        self.assertEqual(sqlite_builder._map_sql_type("bigint"), "INTEGER")
        self.assertEqual(pg_builder._map_sql_type("text"), "TEXT")
        self.assertEqual(pg_builder._map_sql_type("custom_type"), "CUSTOM_TYPE")

    def test_schema_introspector_helpers_cover_postgres_branch(self) -> None:
        fake_inspector = _FakeInspector()
        with patch(
            "src.modules.runtime_schema.infrastructure.schema_introspector.inspect",
            return_value=fake_inspector,
        ):
            payload = SqlAlchemySchemaIntrospector._collect_schema_payload(
                _FakeSyncSession(),
                "tenant_a",
                "postgresql",
            )
        snapshot = SqlAlchemySchemaIntrospector._to_snapshot(payload)
        self.assertIsInstance(snapshot, SchemaSnapshot)
        self.assertIn("accounts", snapshot.tables)
        accounts = snapshot.tables["accounts"]
        self.assertTrue(any(column.is_primary_key for column in accounts.columns))
        self.assertTrue(any(index.name == "idx_accounts_id" for index in accounts.indexes))
        self.assertEqual(
            SqlAlchemySchemaIntrospector._normalize_sql_type("character varying(255)"),
            "varchar(255)",
        )
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("timestamp"), "timestamp_tz")
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("UUID"), "uuid")
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("jsonb"), "json")
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("bool"), "boolean")
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("bigint"), "bigint")
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("int"), "bigint")
        self.assertEqual(SqlAlchemySchemaIntrospector._normalize_sql_type("unknown"), "text")

    def test_schema_lock_key_signed_and_unsigned(self) -> None:
        tenant_id = _tenant_id()

        low_digest = MagicMock()
        low_digest.digest.return_value = b"\x7f" + b"\x00" * 19
        with patch("src.modules.runtime_schema.infrastructure.schema_lock.sha1", return_value=low_digest):
            lock_key = SqlAlchemySchemaLockService._lock_key(
                tenant_id=tenant_id,
                schema="tenant_a",
            )
        self.assertGreaterEqual(lock_key, 0)

        high_digest = MagicMock()
        high_digest.digest.return_value = b"\xff" * 20
        with patch(
            "src.modules.runtime_schema.infrastructure.schema_lock.sha1",
            return_value=high_digest,
        ):
            lock_key = SqlAlchemySchemaLockService._lock_key(
                tenant_id=tenant_id,
                schema="tenant_a",
            )
        self.assertLess(lock_key, 0)


if __name__ == "__main__":
    unittest.main()
