from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.operations import (
    AddForeignKeyOperation,
    CreateTableOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
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
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)
from src.modules.schema_registry.seed.schema_seed import SCHEMA_SEED


REMOVED_OBJECTS = {
    "product",
    "product_category",
    "broadcast",
    "segment_definition",
    "segment_version",
    "segment_static_member",
    "segment_snapshot",
    "segment_snapshot_member",
}

REMOVED_TABLES = {
    "products",
    "product_categories",
    "broadcasts",
    "segment_definitions",
    "segment_versions",
    "segment_static_members",
    "segment_snapshots",
    "segment_snapshot_members",
}


def _uuid_column(name: str) -> ColumnSnapshot:
    return ColumnSnapshot(
        name=name,
        sql_preset=SqlTypePresetEnum.UUID,
        is_nullable=False,
        default_value=None,
    )


class SchemaSeedRuntimeCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_seed_keeps_core_objects_without_removed_models(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )
        seeded_objects = {object_seed.singular_name for object_seed in seed.objects}

        self.assertFalse(REMOVED_OBJECTS & seeded_objects)

        contact = seed.get_object("contact")
        company = seed.get_object("company")
        self.assertIsNotNone(contact)
        self.assertIsNotNone(company)
        assert contact is not None
        assert company is not None
        self.assertEqual(company.plural_name, "companies")
        self.assertIn("legal_name", {field.name for field in company.fields})
        self.assertTrue(
            any(
                relation.name == "contact_companies"
                and relation.relation_type.value == "many_to_many"
                for relation in contact.relations
            )
        )

        expected_communication_objects = {
            "communication_provider_connector",
            "communication_provider_message_type",
            "communication_provider_connection",
            "communication_message_template",
            "communication_template_version",
            "communication_request",
            "communication_outbound_message",
            "communication_delivery_attempt",
            "communication_delivery_event",
        }
        self.assertTrue(expected_communication_objects <= seeded_objects)
        for object_name in expected_communication_objects:
            object_seed = seed.get_object(object_name)
            assert object_seed is not None
            self.assertIn("id", {field.name for field in object_seed.fields})
            self.assertNotIn("tenant_id", {field.name for field in object_seed.fields})

        for object_name in ("communication_request", "communication_outbound_message"):
            object_seed = seed.get_object(object_name)
            assert object_seed is not None
            field_names = {field.name for field in object_seed.fields}
            self.assertIn("recipient_identifier_type", field_names)
            self.assertIn("recipient_address", field_names)
            self.assertIn("recipient_snapshot", field_names)

    def test_create_plan_excludes_removed_runtime_tables(self) -> None:
        plan_service = PostgresSchemaPlanService(
            field_type_catalog=FieldTypeCatalog(),
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        )
        seed_service = SchemaSeedService(
            seed_reader=None,  # type: ignore[arg-type]
            field_type_catalog=FieldTypeCatalog(),
        )
        seed = seed_service._normalize(SCHEMA_SEED)  # noqa: SLF001

        plan = plan_service.build_create_plan(
            schema_name="dnk_test",
            seed=seed,
        )

        tables = {
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        }
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertIn("contacts", tables)
        self.assertIn("companies", tables)
        self.assertIn("contacts_companies", tables)
        self.assertTrue(
            any(
                fk.constraint_name == "fk_contacts_companies_contact_id_contacts"
                and fk.table_name == "contacts_companies"
                and fk.target_table_name == "contacts"
                for fk in foreign_keys
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name == "fk_contacts_companies_company_id_companies"
                and fk.table_name == "contacts_companies"
                and fk.target_table_name == "companies"
                for fk in foreign_keys
            )
        )
        self.assertFalse(REMOVED_TABLES & tables)
        self.assertFalse(
            any(
                fk.table_name in REMOVED_TABLES
                or fk.target_table_name in REMOVED_TABLES
                for fk in foreign_keys
            )
        )

    def test_diff_plan_drops_removed_runtime_tables_and_artifacts(self) -> None:
        plan_service = PostgresSchemaPlanService(
            field_type_catalog=FieldTypeCatalog(),
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        )
        seed_service = SchemaSeedService(
            seed_reader=None,  # type: ignore[arg-type]
            field_type_catalog=FieldTypeCatalog(),
        )
        seed = seed_service._normalize(SCHEMA_SEED)  # noqa: SLF001
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="product_categories",
                    columns=(
                        _uuid_column("id"),
                        _uuid_column("parent_category_id"),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="product_categories_id_uq",
                            columns=("id",),
                            is_unique=True,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="fk_product_categories_parent_category_id_product_categories",
                            source_columns=("parent_category_id",),
                            target_table_name="product_categories",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
                TableSnapshot(
                    name="products",
                    columns=(
                        _uuid_column("id"),
                        _uuid_column("category_id"),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="products_sku_uq",
                            columns=("sku",),
                            is_unique=True,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="fk_products_category_id_product_categories",
                            source_columns=("category_id",),
                            target_table_name="product_categories",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
                TableSnapshot(
                    name="broadcasts",
                    columns=(_uuid_column("id"),),
                    indexes=(
                        IndexSnapshot(
                            name="broadcasts_status_idx",
                            columns=("status",),
                            is_unique=False,
                        ),
                    ),
                ),
                TableSnapshot(
                    name="segment_definitions",
                    columns=(_uuid_column("id"),),
                ),
                TableSnapshot(
                    name="segment_versions",
                    columns=(
                        _uuid_column("id"),
                        _uuid_column("segment_definition_id"),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="fk_segment_versions_segment_definition_id_segment_definitions",
                            source_columns=("segment_definition_id",),
                            target_table_name="segment_definitions",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
                TableSnapshot(
                    name="segment_static_members",
                    columns=(_uuid_column("id"),),
                ),
                TableSnapshot(
                    name="segment_snapshots",
                    columns=(_uuid_column("id"),),
                ),
                TableSnapshot(
                    name="segment_snapshot_members",
                    columns=(_uuid_column("id"),),
                ),
            ),
        )

        plan = plan_service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )

        dropped_tables = {
            operation.table_name
            for operation in plan.destructive_operations
            if isinstance(operation, DropTableOperation)
        }
        dropped_indexes = {
            operation.index_name
            for operation in plan.destructive_operations
            if isinstance(operation, DropIndexOperation)
        }
        dropped_foreign_keys = {
            operation.constraint_name
            for operation in plan.destructive_operations
            if isinstance(operation, DropForeignKeyOperation)
        }

        self.assertTrue(REMOVED_TABLES <= dropped_tables)
        self.assertTrue(
            {
                "products_sku_uq",
                "product_categories_id_uq",
                "broadcasts_status_idx",
            }
            <= dropped_indexes
        )
        self.assertTrue(
            {
                "fk_products_category_id_product_categories",
                "fk_product_categories_parent_category_id_product_categories",
                "fk_segment_versions_segment_definition_id_segment_definitions",
            }
            <= dropped_foreign_keys
        )


__all__ = ["SchemaSeedRuntimeCleanupTests"]
