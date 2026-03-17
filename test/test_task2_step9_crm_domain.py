from __future__ import annotations

import unittest

from src.modules.crm.domain import (
    CompanyEntity,
    ContactEntity,
    InvalidCompanyNameError,
    InvalidContactFirstNameError,
    InvalidContactLastNameError,
    InvalidContactMiddleNameError,
)


class TestCrmDomainStep9(unittest.TestCase):
    def test_contact_create_normalizes_names(self) -> None:
        contact = ContactEntity.create(
            last_name="  Doe  ",
            first_name="  John ",
            middle_name="  Allan ",
        )

        self.assertEqual(contact.last_name, "Doe")
        self.assertEqual(contact.first_name, "John")
        self.assertEqual(contact.middle_name, "Allan")

    def test_contact_create_blank_middle_name_becomes_none(self) -> None:
        contact = ContactEntity.create(
            last_name="Doe",
            first_name="John",
            middle_name="   ",
        )
        self.assertIsNone(contact.middle_name)

    def test_contact_create_rejects_blank_first_name(self) -> None:
        with self.assertRaises(InvalidContactFirstNameError):
            ContactEntity.create(last_name="Doe", first_name="   ")

    def test_contact_create_rejects_blank_last_name(self) -> None:
        with self.assertRaises(InvalidContactLastNameError):
            ContactEntity.create(last_name=" ", first_name="John")

    def test_contact_create_rejects_too_long_middle_name(self) -> None:
        with self.assertRaises(InvalidContactMiddleNameError):
            ContactEntity.create(
                last_name="Doe",
                first_name="John",
                middle_name="m" * 256,
            )

    def test_company_create_rejects_blank_company_name(self) -> None:
        with self.assertRaises(InvalidCompanyNameError):
            CompanyEntity.create(last_name="Owner", company_name=" ")

    def test_contact_update_returns_normalized_entity(self) -> None:
        contact = ContactEntity.create(last_name="Doe", first_name="John")
        updated = contact.update(
            last_name=" Roe ",
            first_name=" Jane ",
            middle_name="  A. ",
        )

        self.assertEqual(updated.last_name, "Roe")
        self.assertEqual(updated.first_name, "Jane")
        self.assertEqual(updated.middle_name, "A.")
        self.assertGreaterEqual(updated.updated_at, contact.updated_at)


if __name__ == "__main__":
    unittest.main()
