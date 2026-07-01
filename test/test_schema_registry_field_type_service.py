from __future__ import annotations

import unittest

from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaChangeError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog


class FieldTypeCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = FieldTypeCatalog()
        self.canonicalizer = PostgresFieldCanonicalizer()

    def test_datetime_seed_uses_timestamptz_sql_preset(self) -> None:
        field_type = self.catalog.from_seed_type("datetime")
        self.assertEqual(
            self.canonicalizer.sql_preset_from_field_type(field_type),
            SqlTypePresetEnum.TIMESTAMPTZ,
        )
        self.assertEqual(
            self.canonicalizer.sql_preset_from_postgres_type(
                "timestamp with time zone"
            ),
            SqlTypePresetEnum.TIMESTAMPTZ,
        )
        self.assertEqual(
            self.canonicalizer.sql_preset_from_postgres_type(
                "timestamp without time zone"
            ),
            SqlTypePresetEnum.TIMESTAMP,
        )

    def test_reference_field_uses_uuid_sql_preset(self) -> None:
        field_type = self.catalog.from_seed_type("reference")
        self.assertEqual(
            self.canonicalizer.sql_preset_from_field_type(field_type),
            SqlTypePresetEnum.UUID,
        )

    def test_canonicalizes_seed_and_postgres_defaults_to_same_timestamp_value(
        self,
    ) -> None:
        seed_default = self.canonicalizer.normalize_seed_default(
            raw_default="now()",
            sql_preset=SqlTypePresetEnum.TIMESTAMPTZ,
        )
        postgres_default = self.canonicalizer.normalize_postgres_default(
            raw_default="(now())",
            sql_preset=SqlTypePresetEnum.TIMESTAMPTZ,
        )

        self.assertEqual(seed_default, "CURRENT_TIMESTAMP")
        self.assertEqual(seed_default, postgres_default)

    def test_rejects_unknown_postgres_type(self) -> None:
        with self.assertRaises(UnsupportedSchemaChangeError):
            self.canonicalizer.sql_preset_from_postgres_type("numeric(18,2)")

    def test_normalizes_uuid_generator_default(self) -> None:
        self.assertEqual(
            self.canonicalizer.normalize_seed_default(
                raw_default="gen_random_uuid()",
                sql_preset=SqlTypePresetEnum.UUID,
            ),
            "gen_random_uuid()",
        )
        self.assertEqual(
            self.canonicalizer.normalize_postgres_default(
                raw_default="(gen_random_uuid())",
                sql_preset=SqlTypePresetEnum.UUID,
            ),
            "gen_random_uuid()",
        )
