from __future__ import annotations

import unittest

from src.modules.schema_registry.domain.error import InvalidValueObjectError
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)


class ObjectLabelVOTests(unittest.TestCase):
    def test_allows_labels_at_postgres_identifier_limit(self) -> None:
        singular = "S" * 63
        plural = "P" * 63

        label = ObjectLabelVO(singular=singular, plural=plural)

        self.assertEqual(label.singular, singular)
        self.assertEqual(label.plural, plural)

    def test_rejects_labels_over_postgres_identifier_limit(self) -> None:
        cases = (
            ("singular", "S" * 64, "Contacts", "Object label_singular"),
            ("plural", "Contact", "P" * 64, "Object label_plural"),
        )

        for _case, singular, plural, field_name in cases:
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(
                    InvalidValueObjectError,
                    rf"{field_name} length must be <= 63\.",
                ):
                    ObjectLabelVO(singular=singular, plural=plural)

    def test_trims_labels(self) -> None:
        label = ObjectLabelVO(singular=" Contact ", plural=" Contacts ")

        self.assertEqual(label.singular, "Contact")
        self.assertEqual(label.plural, "Contacts")

    def test_rejects_empty_labels(self) -> None:
        cases = (
            ("singular", " ", "Contacts", "Object label_singular cannot be empty."),
            ("plural", "Contact", " ", "Object label_plural cannot be empty."),
        )

        for _case, singular, plural, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(InvalidValueObjectError, message):
                    ObjectLabelVO(singular=singular, plural=plural)

    def test_rejects_equal_labels_after_trim(self) -> None:
        with self.assertRaisesRegex(
            InvalidValueObjectError,
            "Object label_singular must not be equal to label_plural.",
        ):
            ObjectLabelVO(singular=" Contact ", plural="Contact")
