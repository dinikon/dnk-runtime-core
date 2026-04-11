from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.value_object import ContactIdVO


class ContactEntityTests(unittest.TestCase):
    def test_rename_preserves_status_and_tags_when_not_provided(self) -> None:
        created_at = datetime.now(UTC)
        updated_at = created_at + timedelta(minutes=1)
        contact = ContactEntity.create(
            id_=ContactIdVO.from_value(uuid4()),
            now=created_at,
            first_name="Jane",
            last_name="Doe",
            status="lead",
            tags=("vip",),
        )

        contact.rename(
            now=updated_at,
            first_name="Janet",
            last_name="Doe",
            status=None,
            tags=None,
        )

        self.assertEqual(contact.contact_name.first_name, "Janet")
        self.assertEqual(contact.status, "lead")
        self.assertEqual(contact.tags, ["vip"])

    def test_rename_allows_clearing_tags_with_empty_tuple(self) -> None:
        created_at = datetime.now(UTC)
        updated_at = created_at + timedelta(minutes=1)
        contact = ContactEntity.create(
            id_=ContactIdVO.from_value(uuid4()),
            now=created_at,
            first_name="Jane",
            last_name="Doe",
            status="lead",
            tags=("vip",),
        )

        contact.rename(
            now=updated_at,
            first_name="Jane",
            last_name="Doe",
            status=None,
            tags=(),
        )

        self.assertEqual(contact.status, "lead")
        self.assertEqual(contact.tags, [])
