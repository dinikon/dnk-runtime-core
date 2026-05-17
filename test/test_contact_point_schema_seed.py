from __future__ import annotations

import unittest

from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)


class ContactPointSchemaSeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_seed_contains_contact_point_objects(self) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        contact_point = seed.get_object("contact_point")
        contact_point_binding = seed.get_object("contact_point_binding")

        self.assertIsNotNone(contact_point)
        self.assertIsNotNone(contact_point_binding)
        assert contact_point is not None
        assert contact_point_binding is not None

        self.assertEqual(contact_point.plural_name, "contact_points")
        self.assertEqual(
            [field.name for field in contact_point.fields],
            [
                "id",
                "created_at",
                "updated_at",
                "contact_point_type",
                "raw_value",
                "display_value",
                "normalized_value",
                "normalized_hash",
            ],
        )
        self.assertEqual(
            {
                field.name: (field.type, field.is_nullable, field.default)
                for field in contact_point.fields
            },
            {
                "id": ("uuid", False, "gen_random_uuid()"),
                "created_at": ("datetime", False, "CURRENT_TIMESTAMP"),
                "updated_at": ("datetime", False, "CURRENT_TIMESTAMP"),
                "contact_point_type": ("text", False, None),
                "raw_value": ("text", False, None),
                "display_value": ("text", False, None),
                "normalized_value": ("text", False, None),
                "normalized_hash": ("text", False, None),
            },
        )

        self.assertEqual(contact_point_binding.plural_name, "contact_point_bindings")
        self.assertEqual(
            [field.name for field in contact_point_binding.fields],
            [
                "id",
                "created_at",
                "updated_at",
                "contact_point_id",
                "contact_point_type",
                "owner_object_id",
                "owner_record_id",
                "owner_type",
                "role",
                "is_primary",
            ],
        )
        self.assertEqual(
            {
                field.name: (field.type, field.is_nullable, field.default)
                for field in contact_point_binding.fields
            },
            {
                "id": ("uuid", False, "gen_random_uuid()"),
                "created_at": ("datetime", False, "CURRENT_TIMESTAMP"),
                "updated_at": ("datetime", False, "CURRENT_TIMESTAMP"),
                "contact_point_id": ("reference", False, None),
                "contact_point_type": ("text", False, None),
                "owner_object_id": ("uuid", False, None),
                "owner_record_id": ("uuid", False, None),
                "owner_type": ("text", False, None),
                "role": ("text", False, None),
                "is_primary": ("bool", False, "false"),
            },
        )

    async def test_default_seed_contains_contact_point_indexes_and_relation(
        self,
    ) -> None:
        service = SchemaSeedService(
            PythonModuleSeedReader(),
            FieldTypeCatalog(),
        )

        seed = await service.load(
            seed_path="src.modules.schema_registry.seed.schema_seed"
        )

        contact_point = seed.get_object("contact_point")
        contact_point_binding = seed.get_object("contact_point_binding")

        assert contact_point is not None
        assert contact_point_binding is not None

        self.assertEqual(
            {
                index.name: (index.fields, index.is_unique)
                for index in contact_point.indexes
            },
            {
                "uniq_contact_point_type_hash": (
                    ("contact_point_type", "normalized_hash"),
                    True,
                ),
                "idx_contact_point_hash": (("normalized_hash",), False),
            },
        )
        self.assertEqual(
            {
                index.name: (index.fields, index.is_unique)
                for index in contact_point_binding.indexes
            },
            {
                "idx_cpb_owner": (
                    ("owner_object_id", "owner_record_id"),
                    False,
                ),
                "idx_cpb_contact_point_id": (("contact_point_id",), False),
                "idx_cpb_owner_type_role": (
                    ("owner_object_id", "owner_record_id", "owner_type", "role"),
                    False,
                ),
                "uniq_cpb_point_owner_role": (
                    (
                        "contact_point_id",
                        "owner_object_id",
                        "owner_record_id",
                        "owner_type",
                        "role",
                    ),
                    True,
                ),
            },
        )

        self.assertEqual(len(contact_point_binding.relations), 1)
        relation = contact_point_binding.relations[0]
        self.assertEqual(relation.name, "contact_point_bindings_contact_point")
        self.assertEqual(relation.relation_type.value, "many_to_one")
        self.assertEqual(relation.source_object, "contact_point_binding")
        self.assertEqual(relation.target_object, "contact_point")
        self.assertEqual(relation.owning_object, "contact_point_binding")
        self.assertEqual(relation.fk_field, "contact_point_id")
        self.assertEqual(relation.referenced_object, "contact_point")
        self.assertEqual(relation.referenced_field, "id")
        self.assertEqual(relation.on_delete, "restrict")
