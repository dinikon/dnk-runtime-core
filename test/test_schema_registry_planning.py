from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    AlterColumnDefaultOperation,
    AlterColumnNullableOperation,
    AlterColumnTypeOperation,
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
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
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
                            type="reference",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company",
                            relation_type="many_to_one",
                            source_object="contact",
                            target_object="company",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_create_plan(
            schema_name="dnk_test",
            seed=self._normalize(seed),
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
                            type="reference",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company",
                            relation_type="one_to_one",
                            source_object="contact",
                            target_object="company",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
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
                operation.index_name == "uq_contacts_company_id"
                and operation.columns == ("company_id",)
                for operation in unique_indexes
            )
        )
        self.assertEqual(
            foreign_keys[0].constraint_name,
            "fk_contacts_company_id_companies",
        )

    def test_one_to_many_relation_adds_fk_to_owning_table(self) -> None:
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
                    relations=(
                        RelationSeed(
                            name="company_contacts",
                            relation_type="one_to_many",
                            source_object="company",
                            target_object="contact",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
                            source_relation_name="contacts",
                            target_relation_name="company",
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
                            type="reference",
                            label="Company ID",
                            is_nullable=True,
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_create_plan(
            schema_name="dnk_test",
            seed=self._normalize(seed),
        )

        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]
        indexes = [
            operation
            for operation in plan.operations
            if isinstance(operation, CreateIndexOperation)
        ]

        self.assertTrue(
            any(
                fk.constraint_name == "fk_contacts_company_id_companies"
                and fk.table_name == "contacts"
                and fk.target_table_name == "companies"
                for fk in foreign_keys
            )
        )
        self.assertTrue(
            any(
                index.index_name == "idx_contacts_company_id"
                and index.columns == ("company_id",)
                for index in indexes
            )
        )

    def test_many_to_many_relation_adds_join_table_indexes_and_fks(self) -> None:
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
                    relations=(
                        RelationSeed(
                            name="contact_tags",
                            relation_type="many_to_many",
                            source_object="contact",
                            target_object="tag",
                            relation_table_name="contacts_tags",
                            source_join_column_name="contact_id",
                            target_join_column_name="tag_id",
                            on_delete="cascade",
                        ),
                    ),
                ),
                ObjectSeed(
                    singular_name="tag",
                    plural_name="tags",
                    singular_label="Tag",
                    plural_label="Tags",
                    description="Tags.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
            ),
        )

        plan = self.service.build_create_plan(
            schema_name="dnk_test",
            seed=self._normalize(seed),
        )

        create_tables = [
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        ]
        indexes = [
            operation
            for operation in plan.operations
            if isinstance(operation, CreateIndexOperation)
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertIn("contacts_tags", create_tables)
        self.assertTrue(
            any(
                index.index_name == "uq_contacts_tags_contact_id_tag_id"
                and index.columns == ("contact_id", "tag_id")
                and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name == "fk_contacts_tags_contact_id_contacts"
                and fk.table_name == "contacts_tags"
                and fk.target_table_name == "contacts"
                and fk.on_delete == "cascade"
                for fk in foreign_keys
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name == "fk_contacts_tags_tag_id_tags"
                and fk.target_table_name == "tags"
                for fk in foreign_keys
            )
        )

    def test_build_diff_plan_adds_referenced_unique_index_before_m2m_fk(
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
                    ),
                    indexes=(
                        IndexSeed(
                            name="contacts_id_uq",
                            fields=("id",),
                            is_unique=True,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contact_tags",
                            relation_type="many_to_many",
                            source_object="contact",
                            target_object="tag",
                            relation_table_name="contacts_tags",
                            source_join_column_name="contact_id",
                            target_join_column_name="tag_id",
                            on_delete="restrict",
                        ),
                    ),
                ),
                ObjectSeed(
                    singular_name="tag",
                    plural_name="tags",
                    singular_label="Tag",
                    plural_label="Tags",
                    description="Tags.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                    indexes=(
                        IndexSeed(
                            name="tags_id_uq",
                            fields=("id",),
                            is_unique=True,
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
                TableSnapshot(
                    name="tags",
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="tags_id_uq",
                            columns=("id",),
                            is_unique=True,
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
        operation_positions = {
            getattr(
                operation, "index_name", getattr(operation, "constraint_name", "")
            ): index
            for index, operation in enumerate(plan.operations)
        }

        self.assertLess(
            operation_positions["contacts_id_uq"],
            operation_positions["fk_contacts_tags_contact_id_contacts"],
        )

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
                            type="reference",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company",
                            relation_type="one_to_one",
                            source_object="contact",
                            target_object="company",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
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

    def test_build_diff_plan_upgrades_datetime_columns_to_timestamptz(
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
                            name="created_at",
                            type="datetime",
                            label="Created At",
                            is_nullable=False,
                            default="CURRENT_TIMESTAMP",
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
                            name="created_at",
                            sql_preset=SqlTypePresetEnum.TIMESTAMP,
                            is_nullable=False,
                            default_value="CURRENT_TIMESTAMP",
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
                isinstance(item, AlterColumnTypeOperation)
                and item.table_name == "contacts"
                and item.column_name == "created_at"
                and item.from_sql_preset == SqlTypePresetEnum.TIMESTAMP
                and item.to_sql_preset == SqlTypePresetEnum.TIMESTAMPTZ
                for item in plan.operations
            )
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
