from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.identity.infrastructure.repository.user_repository import (
    SqlAlchemyUserRepository,
)


class _ScalarSequenceResult:
    def __init__(self, items):
        self._items = list(items)

    def one_or_none(self):
        if not self._items:
            return None
        if len(self._items) == 1:
            return self._items[0]
        raise AssertionError("Expected zero or one result in test stub.")

    def all(self):
        return list(self._items)


class _AsyncSessionStub:

    def __init__(self, *, scalars_results=None) -> None:
        self._scalars_results = list(scalars_results or [])

    async def scalars(self, statement):
        if not self._scalars_results:
            return _ScalarSequenceResult([])

        items = self._scalars_results.pop(0)
        if items is None:
            return _ScalarSequenceResult([])
        if isinstance(items, list):
            return _ScalarSequenceResult(items)
        return _ScalarSequenceResult([items])


class SqlAlchemyUserRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime.now(UTC)
        self.user_id = uuid4()
        self.tenant_id = uuid4()
        self.user_model = UserModel(
            id=self.user_id,
            tenant_id=self.tenant_id,
            status="active",
            last_name="Doe",
            first_name="John",
            middle_name=None,
            avatar=None,
            interface_language="uk",
            interface_theme="system",
            timezone="Europe/Kyiv",
            last_login_at=None,
            last_active_at=self.now,
            last_login_ip=None,
            initialized_at=None,
            created_at=self.now,
            updated_at=self.now,
        )
        self.primary_email_model = UserEmailModel(
            id=uuid4(),
            user_id=self.user_id,
            email="john@example.com",
            is_primary=True,
            is_verified=True,
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )

    async def test_get_by_id_returns_none_when_user_is_missing(self) -> None:
        repository = SqlAlchemyUserRepository(
            _AsyncSessionStub(
                scalars_results=[None],
            )
        )

        result = await repository.get_by_id(self.user_id)

        self.assertIsNone(result)

    async def test_get_by_id_maps_user_and_emails_without_mapper_module(self) -> None:
        repository = SqlAlchemyUserRepository(
            _AsyncSessionStub(
                scalars_results=[self.user_model, [self.primary_email_model]],
            )
        )

        result = await repository.get_by_id(self.user_id)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, self.user_model.id)
        self.assertEqual(result.tenant_id, self.user_model.tenant_id)
        self.assertEqual(result.first_name, "John")
        self.assertEqual(len(result.emails), 1)
        self.assertEqual(result.emails[0].email, "john@example.com")
        self.assertTrue(result.emails[0].is_primary)
        self.assertTrue(result.emails[0].is_verified)

    async def test_get_by_tenant_and_primary_email_returns_none_when_user_missing(
        self,
    ) -> None:
        repository = SqlAlchemyUserRepository(
            _AsyncSessionStub(
                scalars_results=[None],
            )
        )

        result = await repository.get_by_tenant_and_primary_email(
            self.tenant_id,
            "john@example.com",
        )

        self.assertIsNone(result)

    async def test_get_by_tenant_and_primary_email_maps_user_and_emails(self) -> None:
        repository = SqlAlchemyUserRepository(
            _AsyncSessionStub(
                scalars_results=[self.user_model, [self.primary_email_model]],
            )
        )

        result = await repository.get_by_tenant_and_primary_email(
            self.tenant_id,
            "john@example.com",
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, self.user_model.id)
        self.assertEqual(result.last_name, "Doe")
        self.assertEqual(result.timezone, "Europe/Kyiv")
        self.assertEqual(len(result.emails), 1)
        self.assertEqual(result.emails[0].user_id, self.user_id)
        self.assertEqual(result.emails[0].email, "john@example.com")


__all__ = ["SqlAlchemyUserRepositoryTests"]
