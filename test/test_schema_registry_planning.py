from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    AlterColumnDefaultOperation,
    AlterColumnNullableOperation,
    CreateIndexOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropForeignKeyOperation,
    DropTableOperation,
)
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    PhysicalSchemaSnapshot,
    TableSnapshot,
)
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.postgres_schema_plan_service import (
    PostgresSchemaPlanService,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaChangeError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class PostgresSchemaPlanServiceTests(unittest.TestCase):

    def setUp(self) -> None:
        self.field_type_catalog = FieldTypeCatalog()
        self.service = PostgresSchemaPlanService(
            field_type_catalog=self.field_type_catalog,
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        )
        self.seed_service = SchemaSeedService(
            seed_reader=None,  # type: ignore[arg-type]
            field_type_catalog=self.field_type_catalog,
        )

    def _normalize(self, seed: SchemaSeed):
        return self.seed_service._normalize(seed)  # noqa: SLF001

    def test_build_create_plan_uses_plural_name_for_tables(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="company",
                    plural_name="companies",
                    singular_label="Company",
                    plural_label="Companies",
                    description="Companies.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="company_id",
                            type="uuid",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company_id_fk",
                            relation_type="many_to_one",
                            source_field="company_id",
                            target_object="company",
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_create_plan(
            schema_name="dnk_test",
            seed=seed,
        )

        create_tables = [
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertEqual(create_tables, ["companies", "contacts"])
        self.assertEqual(foreign_keys[0].table_name, "contacts")
        self.assertEqual(foreign_keys[0].target_table_name, "companies")

    def test_one_to_one_relation_adds_fk_and_unique_index(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="company",
                    plural_name="companies",
                    singular_label="Company",
                    plural_label="Companies",
                    description="Companies.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="company_id",
                            type="uuid",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company_id_fk",
                            relation_type="one_to_one",
                            source_field="company_id",
                            target_object="company",
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_create_plan(
            schema_name="dnk_test",
            seed=self._normalize(seed),
        )

        unique_indexes = [
            operation
            for operation in plan.operations
            if isinstance(operation, CreateIndexOperation) and operation.is_unique
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertTrue(
            any(
                operation.index_name == "contacts_company_id_one_to_one_uq"
                and operation.columns == ("company_id",)
                for operation in unique_indexes
            )
        )
        self.assertEqual(foreign_keys[0].constraint_name, "contacts_company_id_fk")

    def test_raw_one_to_one_seed_does_not_degrade_to_plain_fk(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="company",
                    plural_name="companies",
                    singular_label="Company",
                    plural_label="Companies",
                    description="Companies.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="company_id",
                            type="uuid",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company_id_fk",
                            relation_type="one_to_one",
                            source_field="company_id",
                            target_object="company",
                        ),
                    ),
                ),
            ),
        )

        with self.assertRaises(UnsupportedSchemaChangeError):
            self.service.build_create_plan(schema_name="dnk_test", seed=seed)

    def test_build_diff_plan_full_sync_marks_destructive_operations(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="last_name",
                            type="text",
                            label="Last Name",
                            is_nullable=True,
                        ),
                    ),
                    relations=(),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                        ColumnSnapshot(
                            name="legacy_name",
                            sql_preset=SqlTypePresetEnum.TEXT,
                            is_nullable=True,
                            default_value=None,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="contacts_legacy_fk",
                            source_columns=("legacy_name",),
                            target_table_name="legacy",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
                TableSnapshot(
                    name="legacy",
                    columns=(),
                ),
            ),
        )

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )

        self.assertTrue(plan.has_destructive_changes)
        self.assertTrue(
            any(
                isinstance(item, DropForeignKeyOperation)
                for item in plan.destructive_operations
            )
        )
        self.assertTrue(
            any(
                isinstance(item, DropColumnOperation)
                for item in plan.destructive_operations
            )
        )
        self.assertTrue(
            any(
                isinstance(item, DropTableOperation)
                for item in plan.destructive_operations
            )
        )
        self.assertTrue(
            any(isinstance(item, AddColumnOperation) for item in plan.operations)
        )

    def test_build_diff_plan_drops_foreign_keys_for_removed_table(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="deals",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                        ColumnSnapshot(
                            name="company_id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="deals_company_id_fk",
                            source_columns=("company_id",),
                            target_table_name="companies",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )

        self.assertTrue(
            any(
                isinstance(item, DropForeignKeyOperation)
                and item.constraint_name == "deals_company_id_fk"
                for item in plan.destructive_operations
            )
        )
        self.assertTrue(
            any(
                isinstance(item, DropTableOperation) and item.table_name == "deals"
                for item in plan.destructive_operations
            )
        )

    def test_build_diff_plan_preserves_custom_tables_outside_seed(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="c_deals",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                        ColumnSnapshot(
                            name="company_id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=True,
                            default_value=None,
                        ),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="c_deals_id_uq",
                            columns=("id",),
                            is_unique=True,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="c_deals_company_id_fk",
                            source_columns=("company_id",),
                            target_table_name="companies",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )

        self.assertEqual(plan.operations, [])

    def test_build_diff_plan_allows_retained_column_default_change(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id",
                            type="uuid",
                            label="ID",
                            is_nullable=False,
                            default="gen_random_uuid()",
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )

        self.assertTrue(
            any(
                isinstance(item, AlterColumnDefaultOperation)
                and item.table_name == "contacts"
                and item.column_name == "id"
                and item.default_value == "gen_random_uuid()"
                for item in plan.operations
            )
        )

    def test_build_diff_plan_rejects_required_added_column_without_default(
        self,
    ) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="last_name",
                            type="text",
                            label="Last Name",
                            is_nullable=False,
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                ),
            ),
        )

        with self.assertRaises(UnsupportedSchemaChangeError):
            self.service.build_diff_plan(
                schema_name="dnk_test",
                seed=self._normalize(seed),
                actual_schema=actual_schema,
            )

    def test_build_diff_plan_allows_required_added_column_with_default(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="last_name",
                            type="text",
                            label="Last Name",
                            is_nullable=False,
                            default="'unknown'",
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=self._normalize(seed),
            actual_schema=actual_schema,
        )

        self.assertTrue(
            any(
                isinstance(item, AddColumnOperation)
                and item.column_name == "last_name"
                and item.default_value == "'unknown'"
                for item in plan.operations
            )
        )

    def test_build_diff_plan_allows_required_columns_for_new_table(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(schema_name="dnk_test", tables=())

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=self._normalize(seed),
            actual_schema=actual_schema,
        )

        self.assertTrue(
            any(
                isinstance(item, AddColumnOperation)
                and item.table_name == "contacts"
                and item.column_name == "id"
                and not item.is_nullable
                for item in plan.operations
            )
        )

    def test_build_diff_plan_fails_on_retained_column_shape_mismatch(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.TEXT,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                ),
            ),
        )

        with self.assertRaises(UnsupportedSchemaChangeError):
            self.service.build_diff_plan(
                schema_name="dnk_test",
                seed=seed,
                actual_schema=actual_schema,
            )

    def test_build_diff_plan_allows_retained_column_drop_not_null(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="last_name",
                            type="text",
                            label="Last Name",
                            is_nullable=True,
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                        ColumnSnapshot(
                            name="last_name",
                            sql_preset=SqlTypePresetEnum.TEXT,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )

        self.assertTrue(
            any(
                isinstance(item, AlterColumnNullableOperation)
                and item.table_name == "contacts"
                and item.column_name == "last_name"
                and item.is_nullable
                for item in plan.operations
            )
        )

    def test_build_diff_plan_fails_on_retained_column_set_not_null(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="last_name",
                            type="text",
                            label="Last Name",
                            is_nullable=False,
                        ),
                    ),
                ),
            ),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                        ColumnSnapshot(
                            name="last_name",
                            sql_preset=SqlTypePresetEnum.TEXT,
                            is_nullable=True,
                            default_value=None,
                        ),
                    ),
                ),
            ),
        )

        with self.assertRaises(UnsupportedSchemaChangeError):
            self.service.build_diff_plan(
                schema_name="dnk_test",
                seed=seed,
                actual_schema=actual_schema,
            )
