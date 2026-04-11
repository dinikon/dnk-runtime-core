from __future__ import annotations

import unittest

from src.modules.crm.domain.contact.error import InvalidContactNameError
from src.modules.crm.domain.contact.value_object import ContactNameVO


class ContactNameVOTests(unittest.TestCase):
    def test_first_name_none_is_rejected(self) -> None:
        with self.assertRaises(InvalidContactNameError):
            ContactNameVO(
                first_name=None,  # type: ignore[arg-type]
                last_name="Doe",
                middle_name=None,
            )

    def test_first_name_empty_string_is_allowed(self) -> None:
        value = ContactNameVO(
            first_name="",
            last_name="Doe",
            middle_name=None,
        )
        self.assertEqual(value.first_name, "")

    def test_last_name_and_middle_name_can_be_none(self) -> None:
        value = ContactNameVO(
            first_name="Jane",
            last_name=None,
            middle_name=None,
        )
        self.assertIsNone(value.last_name)
        self.assertIsNone(value.middle_name)
