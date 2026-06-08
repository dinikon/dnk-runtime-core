from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    CreateIndexOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropIndexOperation,
)
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    ColumnSnapshot,
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
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)
from src.modules.schema_registry.seed.schema_seed import SCHEMA_SEED


def _legacy_text_column(name: str) -> ColumnSnapshot:
    return ColumnSnapshot(
        name=name,
        sql_preset=SqlTypePresetEnum.TEXT,
        is_nullable=False,
        default_value=None,
    )


class InventorySchemaSeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_seed_contains_inventory_objects(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        contact = seed.get_object("contact")
        company = seed.get_object("company")
        product = seed.get_object("product")
        category = seed.get_object("product_category")

        self.assertIsNotNone(contact)
        self.assertIsNotNone(company)
        self.assertIsNotNone(product)
        self.assertIsNotNone(category)
        assert contact is not None
        assert company is not None
        assert product is not None
        assert category is not None
        self.assertEqual(company.plural_name, "companies")
        self.assertEqual(product.plural_name, "products")
        self.assertEqual(category.plural_name, "product_categories")
        self.assertIn("legal_name", {field.name for field in company.fields})
        self.assertIn("sku", {field.name for field in product.fields})
        self.assertIn("parent_category_id", {field.name for field in category.fields})
        self.assertTrue(
            any(
                index.name == "products_sku_uq" and index.is_unique
                for index in product.indexes
            )
        )
        self.assertTrue(
            any(
                relation.name == "product_categories_parent_category"
                for relation in category.relations
            )
        )
        self.assertTrue(
            any(
                relation.name == "contact_companies"
                and relation.relation_type.value == "many_to_many"
                for relation in contact.relations
            )
        )

    def test_create_plan_includes_inventory_tables_indexes_and_fks(self) -> None:
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

        tables = [
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        ]
        indexes = [
            operation
            for operation in plan.operations
            if isinstance(operation, CreateIndexOperation)
        ]
        columns = [
            (operation.table_name, operation.column_name)
            for operation in plan.operations
            if isinstance(operation, AddColumnOperation)
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]
        operation_positions = {
            getattr(
                operation, "index_name", getattr(operation, "constraint_name", "")
            ): index
            for index, operation in enumerate(plan.operations)
        }

        self.assertIn("product_categories", tables)
        self.assertIn("products", tables)
        self.assertIn("companies", tables)
        self.assertIn("contacts_companies", tables)
        self.assertTrue(
            any(
                index.index_name == "products_sku_uq" and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name == "product_categories_id_uq" and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name == "contacts_id_uq" and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name == "fk_products_category_id_product_categories"
                and fk.target_table_name == "product_categories"
                for fk in foreign_keys
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name
                == "fk_product_categories_parent_category_id_product_categories"
                and fk.table_name == "product_categories"
                and fk.target_table_name == "product_categories"
                for fk in foreign_keys
            )
        )
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
        self.assertTrue(
            any(
                index.index_name == "uq_contacts_companies_contact_id_company_id"
                and index.is_unique
                for index in indexes
            )
        )
        self.assertLess(
            operation_positions["product_categories_id_uq"],
            operation_positions["fk_products_category_id_product_categories"],
        )
        self.assertLess(
            operation_positions["contacts_id_uq"],
            operation_positions["fk_contacts_companies_contact_id_contacts"],
        )

    async def test_default_seed_contains_communication_runtime_objects(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        expected_objects = {
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
        seeded_objects = {object_seed.singular_name for object_seed in seed.objects}

        self.assertTrue(expected_objects <= seeded_objects)
        for object_name in expected_objects:
            object_seed = seed.get_object(object_name)
            assert object_seed is not None
            self.assertIn("id", {field.name for field in object_seed.fields})
            self.assertNotIn("tenant_id", {field.name for field in object_seed.fields})

        forbidden_source_fields = {
            "contact_id",
            "contact_point_id",
            "contact_point_binding_id",
            "device_endpoint_id",
            "device_endpoint_binding_id",
            "external_identity_id",
            "identity_subject_id",
            "owner_object_id",
            "owner_record_id",
            "context_object_id",
            "context_record_id",
            "recipient_source_ref_id",
        }
        for object_name in ("communication_request", "communication_outbound_message"):
            object_seed = seed.get_object(object_name)
            assert object_seed is not None
            field_names = {field.name for field in object_seed.fields}
            self.assertIn("recipient_identifier_type", field_names)
            self.assertIn("recipient_address", field_names)
            self.assertIn("recipient_snapshot", field_names)
            self.assertFalse(field_names & forbidden_source_fields)

    async def test_default_seed_contains_contact_only_segmentation_objects(
        self,
    ) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        expected_objects = {
            "segment_definition",
            "segment_version",
            "segment_static_member",
            "segment_snapshot",
            "segment_snapshot_member",
        }
        seeded_objects = {object_seed.singular_name for object_seed in seed.objects}

        self.assertTrue(expected_objects <= seeded_objects)
        forbidden_fields = {
            "target_object_id",
            "target_object_name",
            "target_record_id",
        }
        for object_name in expected_objects:
            object_seed = seed.get_object(object_name)
            assert object_seed is not None
            field_names = {field.name for field in object_seed.fields}
            self.assertIn("id", field_names)
            self.assertNotIn("tenant_id", field_names)
            self.assertFalse(field_names & forbidden_fields)

        static_member = seed.get_object("segment_static_member")
        snapshot_member = seed.get_object("segment_snapshot_member")
        assert static_member is not None
        assert snapshot_member is not None
        static_contact = next(
            field for field in static_member.fields if field.name == "contact_id"
        )
        snapshot_contact = next(
            field for field in snapshot_member.fields if field.name == "contact_id"
        )
        self.assertEqual(
            getattr(static_contact.type, "value", static_contact.type),
            "uuid",
        )
        self.assertEqual(
            getattr(snapshot_contact.type, "value", snapshot_contact.type),
            "uuid",
        )

        unique_indexes = {
            index.name
            for object_seed in seed.objects
            if object_seed.singular_name in expected_objects
            for index in object_seed.indexes
            if index.is_unique
        }
        self.assertTrue(
            {
                "ux_segment_versions_definition_version",
                "ux_segment_static_members_definition_contact",
                "ux_segment_snapshot_members_snapshot_contact",
            }
            <= unique_indexes
        )

        for object_name in expected_objects:
            object_seed = seed.get_object(object_name)
            assert object_seed is not None
            for relation in object_seed.relations:
                self.assertIn(relation.source_object, expected_objects)
                self.assertIn(relation.target_object, expected_objects)
                self.assertNotEqual(relation.target_object, "contact")
                self.assertNotEqual(relation.referenced_object, "contact")

    def test_create_plan_includes_segmentation_tables_indexes_and_fks(self) -> None:
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

        tables = [
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        ]
        indexes = [
            operation
            for operation in plan.operations
            if isinstance(operation, CreateIndexOperation)
        ]
        columns = [
            (operation.table_name, operation.column_name)
            for operation in plan.operations
            if isinstance(operation, AddColumnOperation)
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertIn("segment_definitions", tables)
        self.assertIn("segment_versions", tables)
        self.assertIn("segment_static_members", tables)
        self.assertIn("segment_snapshots", tables)
        self.assertIn("segment_snapshot_members", tables)
        self.assertTrue(
            any(
                index.index_name == "ux_segment_versions_definition_version"
                and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name == "ux_segment_static_members_definition_contact"
                and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name == "ux_segment_snapshot_members_snapshot_contact"
                and index.is_unique
                for index in indexes
            )
        )
        segmentation_tables = {
            "segment_definitions",
            "segment_versions",
            "segment_static_members",
            "segment_snapshots",
            "segment_snapshot_members",
        }
        self.assertFalse(
            any(
                fk.table_name in segmentation_tables
                and fk.target_table_name == "contacts"
                for fk in foreign_keys
            )
        )
        self.assertTrue(
            any(
                fk.table_name == "segment_versions"
                and fk.target_table_name == "segment_definitions"
                for fk in foreign_keys
            )
        )

    def test_create_plan_includes_communication_tables_indexes_and_fks(self) -> None:
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

        tables = [
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        ]
        indexes = [
            operation
            for operation in plan.operations
            if isinstance(operation, CreateIndexOperation)
        ]
        columns = [
            (operation.table_name, operation.column_name)
            for operation in plan.operations
            if isinstance(operation, AddColumnOperation)
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertIn("communication_provider_connectors", tables)
        self.assertIn("communication_outbound_messages", tables)
        self.assertNotIn(
            ("communication_provider_connections", "connection_code"),
            columns,
        )
        self.assertNotIn(("communication_message_templates", "template_code"), columns)
        self.assertNotIn(("communication_message_templates", "message_class"), columns)
        self.assertNotIn(("communication_requests", "message_class"), columns)
        self.assertNotIn(("communication_outbound_messages", "message_class"), columns)
        self.assertFalse(
            any(
                index.index_name
                in {
                    "communication_provider_connections_code_uq",
                    "communication_message_templates_code_uq",
                    "communication_message_templates_class_idx",
                }
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name == "communication_provider_connectors_code_version_uq"
                and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name
                == "communication_delivery_attempts_outbound_attempt_uq"
                and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name
                == "fk_communication_outbound_messages_communication_reque_79614ab6"
                and fk.target_table_name == "communication_requests"
                for fk in foreign_keys
            )
        )

    async def test_communication_schema_diff_drops_removed_code_and_class_artifacts(
        self,
    ) -> None:
        plan_service = PostgresSchemaPlanService(
            field_type_catalog=FieldTypeCatalog(),
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        )
        seed_service = SchemaSeedService(
            seed_reader=None,  # type: ignore[arg-type]
            field_type_catalog=FieldTypeCatalog(),
        )
        seed = seed_service._normalize(SCHEMA_SEED)  # noqa: SLF001
        create_plan = plan_service.build_create_plan(schema_name="dnk_test", seed=seed)

        desired_columns = {
            operation.table_name: []
            for operation in create_plan.operations
            if isinstance(operation, AddColumnOperation)
        }
        for operation in create_plan.operations:
            if isinstance(operation, AddColumnOperation):
                desired_columns[operation.table_name].append(
                    ColumnSnapshot(
                        name=operation.column_name,
                        sql_preset=operation.sql_preset,
                        is_nullable=operation.is_nullable,
                        default_value=operation.default_value,
                    )
                )

        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="communication_provider_connections",
                    columns=(
                        *desired_columns["communication_provider_connections"],
                        _legacy_text_column("connection_code"),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="communication_provider_connections_code_uq",
                            columns=("connection_code",),
                            is_unique=True,
                        ),
                    ),
                ),
                TableSnapshot(
                    name="communication_message_templates",
                    columns=(
                        *desired_columns["communication_message_templates"],
                        _legacy_text_column("template_code"),
                        _legacy_text_column("message_class"),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="communication_message_templates_code_uq",
                            columns=("template_code",),
                            is_unique=True,
                        ),
                        IndexSnapshot(
                            name="communication_message_templates_class_idx",
                            columns=("message_class",),
                            is_unique=False,
                        ),
                    ),
                ),
                TableSnapshot(
                    name="communication_requests",
                    columns=(
                        *desired_columns["communication_requests"],
                        _legacy_text_column("message_class"),
                    ),
                ),
                TableSnapshot(
                    name="communication_outbound_messages",
                    columns=(
                        *desired_columns["communication_outbound_messages"],
                        _legacy_text_column("message_class"),
                    ),
                ),
            ),
        )

        diff = plan_service.build_diff_plan(
            schema_name="dnk_test",
            seed=seed,
            actual_schema=actual_schema,
        )
        dropped_columns = {
            (operation.table_name, operation.column_name)
            for operation in diff.destructive_operations
            if isinstance(operation, DropColumnOperation)
        }
        dropped_indexes = {
            operation.index_name
            for operation in diff.destructive_operations
            if isinstance(operation, DropIndexOperation)
        }

        self.assertGreaterEqual(len(diff.destructive_operations), 8)
        self.assertIn(
            ("communication_provider_connections", "connection_code"),
            dropped_columns,
        )
        self.assertIn(
            ("communication_message_templates", "template_code"),
            dropped_columns,
        )
        self.assertIn(
            ("communication_message_templates", "message_class"),
            dropped_columns,
        )
        self.assertIn(("communication_requests", "message_class"), dropped_columns)
        self.assertIn(
            ("communication_outbound_messages", "message_class"),
            dropped_columns,
        )
        self.assertIn("communication_provider_connections_code_uq", dropped_indexes)
        self.assertIn("communication_message_templates_code_uq", dropped_indexes)
        self.assertIn("communication_message_templates_class_idx", dropped_indexes)
