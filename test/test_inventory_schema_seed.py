from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.operations import (
    AddForeignKeyOperation,
    CreateIndexOperation,
    CreateTableOperation,
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
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)
from src.modules.schema_registry.seed.schema_seed import SCHEMA_SEED


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
        self.assertIn("company_name", {field.name for field in company.fields})
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
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertIn("communication_provider_connectors", tables)
        self.assertIn("communication_outbound_messages", tables)
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
