import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.identity.application.provisioning.services.user_service import (
    UserService,
)
from src.modules.identity.domain.errors import UserEmailAlreadyExistsError
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.shared.db.base import Base
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


class UserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_tenant_admin_rejects_duplicate_email_in_same_tenant(
        self,
    ) -> None:
        tenant_id = uuid4()
        repository = InMemoryUserRepository(
            duplicate_email_tenants={tenant_id},
        )
        service = UserService(repository)

        with self.assertRaises(UserEmailAlreadyExistsError):
            await service.create_tenant_admin(
                tenant_id=tenant_id,
                first_name="John",
                last_name="Doe",
                email="john.doe@example.com",
            )

        self.assertEqual(repository.added_users, [])

    async def test_create_tenant_admin_allows_same_email_in_other_tenant(self) -> None:
        tenant_id = uuid4()
        other_tenant_id = uuid4()
        repository = InMemoryUserRepository(duplicate_email_tenants={other_tenant_id})
        service = UserService(repository)

        result = await service.create_tenant_admin(
            tenant_id=tenant_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
        )

        self.assertEqual(len(repository.added_users), 1)
        self.assertEqual(repository.added_users[0].tenant_id, tenant_id)
        self.assertEqual(result.user_id, repository.added_users[0].id)
        self.assertEqual(result.user_email_id, repository.added_users[0].emails[0].id)
        self.assertEqual(result.user_status, "active")


class SqlAlchemyUserRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "repo.db"
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_exists_by_tenant_and_email_ignores_deleted_emails(self) -> None:
        now = datetime.now(UTC)
        tenant_id = uuid4()
        other_tenant_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()
        deleted_email = "deleted@example.com"

        async with self._session_factory() as session:
            session.add(
                TenantModel(
                    id=tenant_id,
                    name="Acme",
                    external_id="tenant-acme",
                    status="active",
                    custom_config=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                TenantModel(
                    id=other_tenant_id,
                    name="Beta",
                    external_id="tenant-beta",
                    status="active",
                    custom_config=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                UserModel(
                    id=user_id,
                    tenant_id=tenant_id,
                    status="active",
                    first_name="John",
                    last_name="Doe",
                    middle_name=None,
                    avatar=None,
                    interface__language="uk",
                    interface_theme="system",
                    timezone="Europe/Kyiv",
                    last_login_at=None,
                    last_active_at=now,
                    last_login_ip=None,
                    initialized_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                UserModel(
                    id=other_user_id,
                    tenant_id=other_tenant_id,
                    status="active",
                    first_name="Jane",
                    last_name="Roe",
                    middle_name=None,
                    avatar=None,
                    interface__language="uk",
                    interface_theme="system",
                    timezone="Europe/Kyiv",
                    last_login_at=None,
                    last_active_at=now,
                    last_login_ip=None,
                    initialized_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                UserEmailModel(
                    id=uuid4(),
                    user_id=user_id,
                    email=deleted_email,
                    is_primary=True,
                    is_verified=False,
                    is_deleted=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                UserEmailModel(
                    id=uuid4(),
                    user_id=other_user_id,
                    email=deleted_email,
                    is_primary=True,
                    is_verified=False,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        async with self._session_factory() as session:
            repository = SqlAlchemyUserRepository(session)
            self.assertFalse(
                await repository.exists_by_tenant_and_email(
                    tenant_id,
                    deleted_email,
                )
            )
            self.assertTrue(
                await repository.exists_by_tenant_and_email(
                    other_tenant_id,
                    deleted_email,
                )
            )

            session.add(
                UserEmailModel(
                    id=uuid4(),
                    user_id=user_id,
                    email="active@example.com",
                    is_primary=False,
                    is_verified=False,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        async with self._session_factory() as session:
            repository = SqlAlchemyUserRepository(session)
            self.assertTrue(
                await repository.exists_by_tenant_and_email(
                    tenant_id,
                    "active@example.com",
                )
            )
            self.assertFalse(
                await repository.exists_by_tenant_and_email(
                    other_tenant_id,
                    "active@example.com",
                )
            )


class InMemoryUserRepository:
    def __init__(self, *, duplicate_email_tenants: set[object]) -> None:
        self._duplicate_email_tenants = duplicate_email_tenants
        self.added_users = []

    async def add(self, user) -> None:
        self.added_users.append(user)

    async def get_by_id(self, user_id):
        return None

    async def exists_by_tenant_and_email(
        self,
        tenant_id,
        email: str,
    ) -> bool:
        return tenant_id in self._duplicate_email_tenants
