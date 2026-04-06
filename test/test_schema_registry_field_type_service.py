from __future__ import annotations

import unittest

from src.modules.schema_registry.domain.error import UnsupportedSchemaChangeError
from src.modules.schema_registry.domain.field.enum.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.field.service import FieldTypeService


class FieldTypeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FieldTypeService()

    def test_canonicalizes_seed_and_postgres_types_to_same_sql_preset(self) -> None:
        self.assertEqual(
            self.service.sql_preset_from_seed_type("datetime"),
            SqlTypePresetEnum.TIMESTAMP,
        )
        self.assertEqual(
            self.service.sql_preset_from_postgres_type("timestamp without time zone"),
            SqlTypePresetEnum.TIMESTAMP,
        )

    def test_canonicalizes_seed_and_postgres_defaults_to_same_timestamp_value(
        self,
    ) -> None:
        seed_default = self.service.normalize_seed_default(
            raw_default="now()",
            sql_preset=SqlTypePresetEnum.TIMESTAMP,
        )
        postgres_default = self.service.normalize_postgres_default(
            raw_default="(now())",
            sql_preset=SqlTypePresetEnum.TIMESTAMP,
        )

        self.assertEqual(seed_default, "CURRENT_TIMESTAMP")
        self.assertEqual(seed_default, postgres_default)

    def test_rejects_unknown_postgres_type(self) -> None:
        with self.assertRaises(UnsupportedSchemaChangeError):
            self.service.sql_preset_from_postgres_type("numeric(18,2)")
