from __future__ import annotations

import unittest

from src.modules.schema_registry.domain.error import InvalidValueObjectError
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
    ObjectFeatureCode,
)


class SchemaRegistryObjectFeatureValueObjectTests(unittest.TestCase):
    def test_feature_code_accepts_contact_point(self) -> None:
        feature_code = FeatureCodeVO(" contact_point ")

        self.assertEqual(feature_code.value, "CONTACT_POINT")
        self.assertEqual(
            ObjectFeatureCode.from_value("contact_point").value, "CONTACT_POINT"
        )

    def test_feature_code_rejects_unknown_code(self) -> None:
        with self.assertRaises(InvalidValueObjectError):
            FeatureCodeVO("unknown_feature")

    def test_feature_code_rejects_legacy_contact_points_code(self) -> None:
        with self.assertRaises(InvalidValueObjectError):
            FeatureCodeVO("CONTACT_POINTS")


__all__ = ["SchemaRegistryObjectFeatureValueObjectTests"]
