from __future__ import annotations

import unittest

from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.postgres_schema_plan_service import (
    PostgresSchemaPlanService,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)
from src.modules.schema_registry.seed.contexts import (
    COMMUNICATION_OBJECTS,
    WORKFLOW_OBJECTS,
)
from src.modules.schema_registry.seed.schema_seed import (
    COMMUNICATION_OBJECTS as AGGREGATED_COMMUNICATION_OBJECTS,
)
from src.modules.schema_registry.seed.schema_seed import (
    WORKFLOW_OBJECTS as AGGREGATED_WORKFLOW_OBJECTS,
)


def _object_names(objects: tuple[ObjectSeed, ...]) -> tuple[str, ...]:
    return tuple(object_seed.singular_name for object_seed in objects)


class SchemaSeedContextTests(unittest.IsolatedAsyncioTestCase):
    def test_context_modules_export_expected_object_groups(self) -> None:
        self.assertEqual(
            _object_names(WORKFLOW_OBJECTS),
            ("workflow_application", "workflow_definition"),
        )
        self.assertEqual(
            _object_names(COMMUNICATION_OBJECTS),
            (
                "communication_provider_connector",
                "communication_provider_message_type",
                "communication_provider_connection",
                "communication_message_template",
                "communication_template_version",
                "communication_request",
                "communication_outbound_message",
                "communication_delivery_attempt",
                "communication_delivery_event",
            ),
        )

        self.assertIs(AGGREGATED_WORKFLOW_OBJECTS, WORKFLOW_OBJECTS)
        self.assertIs(AGGREGATED_COMMUNICATION_OBJECTS, COMMUNICATION_OBJECTS)

    async def test_default_seed_path_aggregates_context_objects(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        self.assertEqual(seed.code, "crm")
        self.assertEqual(seed.label, "CRM")
        self.assertEqual(
            _object_names(seed.objects),
            (
                *_object_names(WORKFLOW_OBJECTS),
                *_object_names(COMMUNICATION_OBJECTS),
            ),
        )
        plan = PostgresSchemaPlanService(
            field_type_catalog=FieldTypeCatalog(),
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        ).build_create_plan(schema_name="dnk_test", seed=seed)
        self.assertFalse(
            any("contact_point" in repr(operation) for operation in plan.operations)
        )


if __name__ == "__main__":
    unittest.main()
