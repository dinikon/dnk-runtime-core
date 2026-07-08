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


class WorkflowSchemaSeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_seed_contains_workflow_objects(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        application = seed.get_object("workflow_application")
        definition = seed.get_object("workflow_definition")

        self.assertIsNotNone(application)
        self.assertIsNotNone(definition)
        assert application is not None
        assert definition is not None
        self.assertEqual(application.plural_name, "workflow_applications")
        self.assertEqual(definition.plural_name, "workflow_definitions")

        application_fields = {field.name: field for field in application.fields}
        definition_fields = {field.name: field for field in definition.fields}
        self.assertIn("created_by", application_fields)
        self.assertIn("updated_by", application_fields)
        self.assertIn("active_workflow_definition_id", application_fields)
        self.assertEqual(application_fields["kind"].type, "select")
        self.assertEqual(application_fields["status"].type, "select")
        self.assertEqual(
            application_fields["active_workflow_definition_id"].type,
            "uuid",
        )
        self.assertNotIn("tenant_id", application_fields)

        self.assertEqual(definition_fields["workflow_application_id"].type, "reference")
        self.assertEqual(definition_fields["graph"].type, "json")
        self.assertEqual(definition_fields["features"].type, "json")
        self.assertEqual(definition_fields["environment"].type, "json")
        self.assertTrue(definition_fields["title"].is_nullable)
        self.assertNotIn("tenant_id", definition_fields)

        self.assertTrue(
            any(
                index.name == "workflow_applications_id_uq" and index.is_unique
                for index in application.indexes
            )
        )
        self.assertTrue(
            any(
                index.name == "workflow_definitions_application_version_uq"
                and index.is_unique
                for index in definition.indexes
            )
        )
        self.assertTrue(
            any(
                relation.name == "workflow_definitions_application"
                and relation.source_object == "workflow_definition"
                and relation.target_object == "workflow_application"
                for relation in definition.relations
            )
        )

    def test_create_plan_includes_workflow_tables_indexes_and_fk(self) -> None:
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

        self.assertIn("workflow_applications", tables)
        self.assertIn("workflow_definitions", tables)
        self.assertTrue(
            any(
                index.index_name == "workflow_applications_id_uq" and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index.index_name == "workflow_definitions_application_version_uq"
                and index.is_unique
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                fk.table_name == "workflow_definitions"
                and fk.column_name == "workflow_application_id"
                and fk.target_table_name == "workflow_applications"
                for fk in foreign_keys
            )
        )
        self.assertFalse(
            any(
                fk.table_name == "workflow_applications"
                and fk.column_name == "active_workflow_definition_id"
                for fk in foreign_keys
            )
        )


if __name__ == "__main__":
    unittest.main()
