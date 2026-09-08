from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4
from unittest.mock import AsyncMock

from src.modules.identity.domain.user import User
from src.modules.shared import DomainError
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence import Base
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.tenant_migration_metadata import (
    migration_metadata,
)

from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.identity.infrastructure.repository.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.domain.user import UserEmailIdVO, UserIdVO
from src.modules.shared import EntityIdVO


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

    def mappings(self):
        return self


class _AsyncSessionStub:

    def __init__(self, *, scalars_results=None) -> None:
        self._scalars_results = list(scalars_results or [])
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if not self._scalars_results:
            return _ScalarSequenceResult([])

        items = self._scalars_results.pop(0)
        if items is None:
            return _ScalarSequenceResult([])
        rows = items if isinstance(items, list) else [items]
        return _ScalarSequenceResult(
            [
                {
                    column.name: getattr(row, column.name)
                    for column in row.__table__.columns
                }
                for row in rows
            ]
        )


class SqlAlchemyUserRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime.now(UTC)
        self.user_id = uuid4()
        self.tenant_id = uuid4()
        self.user_model = UserModel(
            id=self.user_id,
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
            ),
            TenantSchemaNaming("test"),
        )

        result = await repository.get_by_id(
            UserIdVO.from_value(self.user_id),
            tenant_id=EntityIdVO.from_value(self.tenant_id),
        )

        self.assertIsNone(result)

    async def test_get_by_id_maps_user_and_emails_without_mapper_module(self) -> None:
        repository = SqlAlchemyUserRepository(
            _AsyncSessionStub(
                scalars_results=[self.user_model, [self.primary_email_model]],
            ),
            TenantSchemaNaming("test"),
        )

        result = await repository.get_by_id(
            UserIdVO.from_value(self.user_id),
            tenant_id=EntityIdVO.from_value(self.tenant_id),
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, UserIdVO.from_value(self.user_model.id))
        self.assertEqual(result.tenant_id, EntityIdVO.from_value(self.tenant_id))
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
            ),
            TenantSchemaNaming("test"),
        )

        result = await repository.get_by_tenant_and_primary_email(
            EntityIdVO.from_value(self.tenant_id),
            "john@example.com",
        )

        self.assertIsNone(result)

    async def test_get_by_tenant_and_primary_email_maps_user_and_emails(self) -> None:
        repository = SqlAlchemyUserRepository(
            _AsyncSessionStub(
                scalars_results=[self.user_model, [self.primary_email_model]],
            ),
            TenantSchemaNaming("test"),
        )

        result = await repository.get_by_tenant_and_primary_email(
            EntityIdVO.from_value(self.tenant_id),
            "john@example.com",
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, UserIdVO.from_value(self.user_model.id))
        self.assertEqual(result.last_name, "Doe")
        self.assertEqual(result.timezone, "Europe/Kyiv")
        self.assertEqual(len(result.emails), 1)
        self.assertEqual(result.emails[0].user_id, UserIdVO.from_value(self.user_id))
        self.assertEqual(
            result.emails[0].id,
            UserEmailIdVO.from_value(self.primary_email_model.id),
        )
        self.assertEqual(result.emails[0].email, "john@example.com")

    def test_models_and_migration_metadata_are_tenant_only(self):
        for model, name, pk in (
            (UserModel, "users", "pk_users"),
            (UserEmailModel, "user_emails", "pk_user_emails"),
        ):
            self.assertNotIn(name, Base.metadata.tables)
            self.assertIs(TenantBase.metadata.tables[f"tenant.{name}"], model.__table__)
            self.assertEqual(model.__table__.primary_key.name, pk)
        self.assertNotIn("tenant_id", UserModel.__table__.c)
        fk = next(iter(UserEmailModel.__table__.foreign_keys))
        self.assertEqual(fk.target_fullname, "tenant.users.id")
        self.assertIsNone(fk.ondelete)
        copied = migration_metadata()
        self.assertEqual(
            next(iter(copied.tables["user_emails"].foreign_keys)).target_fullname,
            "users.id",
        )
        self.assertEqual(
            {index.name for index in UserModel.__table__.indexes}, {"ix_users_status"}
        )
        self.assertEqual(
            {index.name for index in UserEmailModel.__table__.indexes},
            {"ix_user_emails_user_id"},
        )

    async def test_reads_apply_configured_schema_to_user_and_email_queries(self):
        session = _AsyncSessionStub(
            scalars_results=[self.user_model, [self.primary_email_model]]
        )
        naming = TenantSchemaNaming("test")
        tenant_id = EntityIdVO.from_value(self.tenant_id)
        repository = SqlAlchemyUserRepository(session, naming)
        await repository.get_by_id(
            UserIdVO.from_value(self.user_id), tenant_id=tenant_id
        )
        self.assertEqual(len(session.statements), 2)
        for statement in session.statements:
            self.assertEqual(
                statement.get_execution_options()["schema_translate_map"],
                {"tenant": naming.schema_name(tenant_id)},
            )

    async def test_cross_tenant_writes_fail_before_sql(self):
        user = User.create_tenant_admin(
            tenant_id=EntityIdVO.from_value(self.tenant_id),
            first_name="John",
            last_name="Doe",
        )
        other_tenant = EntityIdVO.from_value(uuid4())
        session = AsyncMock()
        repository = SqlAlchemyUserRepository(session, TenantSchemaNaming("dnk_"))
        for operation in (repository.add, repository.update_profile):
            with self.assertRaises(DomainError):
                await operation(user, tenant_id=other_tenant)
        session.execute.assert_not_awaited()


__all__ = ["SqlAlchemyUserRepositoryTests"]
