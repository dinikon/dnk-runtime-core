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

        product = seed.get_object("product")
        category = seed.get_object("product_category")

        self.assertIsNotNone(product)
        self.assertIsNotNone(category)
        assert product is not None
        assert category is not None
        self.assertEqual(product.plural_name, "products")
        self.assertEqual(category.plural_name, "product_categories")
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
                relation.name == "product_categories_parent_category_id_fk"
                for relation in category.relations
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
                fk.constraint_name == "products_category_id_fk"
                and fk.target_table_name == "product_categories"
                for fk in foreign_keys
            )
        )
        self.assertTrue(
            any(
                fk.constraint_name == "product_categories_parent_category_id_fk"
                and fk.table_name == "product_categories"
                and fk.target_table_name == "product_categories"
                for fk in foreign_keys
            )
        )
        self.assertLess(
            operation_positions["product_categories_id_uq"],
            operation_positions["products_category_id_fk"],
        )
