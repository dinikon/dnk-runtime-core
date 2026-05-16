from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.company.value_object import CompanyIdVO


class CompanyEntityTests(unittest.TestCase):
    def test_create_normalizes_legal_name(self) -> None:
        now = datetime.now(UTC)

        company = CompanyEntity.create(
            id_=CompanyIdVO.from_value(uuid4()),
            now=now,
            legal_name="  Acme LLC  ",
        )

        self.assertEqual(company.created_at, now)
        self.assertEqual(company.updated_at, now)
        self.assertEqual(company.legal_name.value, "Acme LLC")

    def test_update_changes_name_and_timestamp(self) -> None:
        created_at = datetime.now(UTC)
        updated_at = created_at + timedelta(minutes=1)
        company = CompanyEntity.create(
            id_=CompanyIdVO.from_value(uuid4()),
            now=created_at,
            legal_name="Acme LLC",
        )

        company.update(now=updated_at, legal_name="Acme Inc.")

        self.assertEqual(company.legal_name.value, "Acme Inc.")
        self.assertEqual(company.updated_at, updated_at)

    def test_update_keeps_timestamp_when_name_is_same(self) -> None:
        created_at = datetime.now(UTC)
        updated_at = created_at + timedelta(minutes=1)
        company = CompanyEntity.create(
            id_=CompanyIdVO.from_value(uuid4()),
            now=created_at,
            legal_name="Acme LLC",
        )

        company.update(now=updated_at, legal_name="  Acme LLC  ")

        self.assertEqual(company.legal_name.value, "Acme LLC")
        self.assertEqual(company.updated_at, created_at)
