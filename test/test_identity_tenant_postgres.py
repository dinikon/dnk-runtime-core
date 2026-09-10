"""Identity isolation and HTTP checks against a disposable PostgreSQL database."""

import os
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, inspect, insert, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.user import User, UserEmailIdVO, UserIdVO
from src.modules.identity.infrastructure.persistence import UserModel, UserEmailModel
from src.modules.identity.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.identity.presentation.depends.infrastructure import (
    get_otp_challenge_store,
    get_session_store,
)
from src.modules.identity.presentation.http.router import router as auth_router
from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence import Base, UnitOfWork
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
    schema_exists,
)
from src.modules.shared.presentation.email.depends import get_email_service
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant import (
    CreateTenantCommand,
    CreateTenantUseCase,
)
from src.modules.tenancy.domain.service import TenantOnboardingService
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.infrastructure.repository import (
    SqlAlchemyTenantRepository,
    SqlAlchemyTenantDomainRepository,
)
from src.modules.tenancy.presentation.depends.infrastructure import (
    get_identity_provisioning_service,
)

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


class _MemoryTokens:
    def __init__(self):
        self.challenges = {}
        self.sessions = {}

    async def create_challenge(self, challenge, ttl_seconds):
        self.challenges[challenge.tenant_id, challenge.token] = challenge

    async def get_challenge(self, tenant_id, token):
        return self.challenges.get((tenant_id, token))

    async def invalidate_challenge(self, tenant_id, token):
        self.challenges.pop((tenant_id, token), None)

    async def create_session(self, session, ttl_seconds):
        self.sessions[session.tenant_id, session.token] = session

    async def get_session(self, tenant_id, token):
        return self.sessions.get((tenant_id, token))

    async def invalidate_session(self, tenant_id, token):
        self.sessions.pop((tenant_id, token), None)


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL 16 database."
)
class IdentityTenantPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming("dnk_")
        self.migrator = TenantMigrator()
        self.schemas = set()
        self.tenant_ids = set()
        self.tag = uuid4().hex
        self.config_patch = patch.object(dnk_config, "SCHEMA_PREFIX", "dnk_")
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        try:
            async with self.engine.begin() as connection:
                for schema in self.schemas:
                    await connection.execute(
                        DropSchema(schema, cascade=True, if_exists=True)
                    )
                await connection.execute(
                    delete(TenantDomainModel).where(
                        TenantDomainModel.tenant_id.in_(self.tenant_ids)
                    )
                )
                await connection.execute(
                    delete(TenantModel).where(TenantModel.id.in_(self.tenant_ids))
                )
        finally:
            await self.engine.dispose()

    async def new_tenant_schema(self):
        tenant_id = EntityIdVO.from_value(uuid4())
        schema = self.naming.schema_name(tenant_id)
        self.schemas.add(schema)
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            await self.migrator.upgrade(connection, schema)
        return tenant_id

    def make_user(self, tenant_id, *, user_id=None, email_id=None, name="Alice"):
        user = User.create_tenant_admin(
            tenant_id=tenant_id, first_name=name, last_name="Tester"
        )
        if user_id:
            user.id = user_id
        email = user.add_email("shared@example.com", is_primary=True)
        if email_id:
            email.id = email_id
        return user

    async def onboard(self, suffix, *, fail_admin=False):
        owner = self

        class RecordingBootstrap(AlembicTenantSchemaBootstrapAdapter):
            async def bootstrap(self, *, context):
                owner.schemas.add(context.schema_name)
                owner.tenant_ids.add(context.tenant_id)
                await super().bootstrap(context=context)

        async with UnitOfWork(self.sessions) as uow:
            provisioning = get_identity_provisioning_service(uow)
            if fail_admin:
                create_admin = provisioning.create_tenant_admin

                async def fail_after_insert(**kwargs):
                    await create_admin(**kwargs)
                    raise RuntimeError("Injected admin failure after insert")

                provisioning.create_tenant_admin = fail_after_insert
            use_case = CreateTenantUseCase(
                tenant_onboarding_service=TenantOnboardingService(
                    SqlAlchemyTenantRepository(uow.session),
                    SqlAlchemyTenantDomainRepository(uow.session),
                ),
                identity_provisioning_service=provisioning,
                tenant_schema_bootstrap_context_factory=TenantSchemaBootstrapContextFactory(
                    schema_prefix="dnk_"
                ),
                tenant_schema_bootstrap_port=RecordingBootstrap(
                    uow.session, self.migrator
                ),
            )
            return await use_case.execute(
                CreateTenantCommand(
                    tenant_name=f"{self.tag}-{suffix}",
                    external_id=f"{self.tag}-{suffix}",
                    tenant_domain_host=f"{self.tag}-{suffix}.example.com",
                    user_first_name="Alice",
                    user_last_name="Tester",
                    user_email="shared@example.com",
                )
            )

    async def test_global_startup_does_not_create_identity_tables(self):
        async with self.engine.begin() as connection:
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema="public")
            )
        self.assertIn("tenants", tables)
        self.assertNotIn("users", tables)
        self.assertNotIn("user_emails", tables)

    async def test_same_ids_and_email_remain_isolated_with_one_repository(self):
        left, right = await self.new_tenant_schema(), await self.new_tenant_schema()
        user_id, email_id = UserIdVO.from_value(uuid4()), UserEmailIdVO.from_value(
            uuid4()
        )
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyUserRepository(uow.session, self.naming)
            connection = await uow.session.connection()
            original_options = connection.sync_connection.get_execution_options()
            original_path = await connection.scalar(text("SHOW search_path"))
            for tenant_id, name in ((left, "Alice"), (right, "Bob")):
                await repository.add(
                    self.make_user(
                        tenant_id, user_id=user_id, email_id=email_id, name=name
                    ),
                    tenant_id=tenant_id,
                )
            for tenant_id, name in ((left, "Alice"), (right, "Bob"), (left, "Alice")):
                user = await repository.get_by_id(user_id, tenant_id=tenant_id)
                self.assertEqual(user.first_name, name)
                self.assertEqual(user.tenant_id, tenant_id)
                self.assertEqual(user.emails[0].id, email_id)
                by_email = await repository.get_by_tenant_and_primary_email(
                    tenant_id, "shared@example.com"
                )
                self.assertEqual(by_email.first_name, name)
                self.assertTrue(
                    await repository.exists_by_tenant_and_email(
                        tenant_id, "shared@example.com"
                    )
                )
                self.assertFalse(
                    await repository.exists_by_tenant_and_email(
                        tenant_id, "absent@example.com"
                    )
                )
            user = await repository.get_by_id(user_id, tenant_id=left)
            user.first_name = "Updated"
            user.updated_at = datetime.now(UTC)
            await repository.update_profile(user, tenant_id=left)
            await repository.mark_email_verified(email_id, tenant_id=left)
            left_user = await repository.get_by_id(user_id, tenant_id=left)
            right_user = await repository.get_by_id(user_id, tenant_id=right)
            self.assertEqual(left_user.first_name, "Updated")
            self.assertTrue(left_user.emails[0].is_verified)
            self.assertEqual(
                left_user.emails[0].updated_at,
                await connection.scalar(text("SELECT CURRENT_TIMESTAMP")),
            )
            self.assertEqual(right_user.first_name, "Bob")
            self.assertFalse(right_user.emails[0].is_verified)
            self.assertEqual(len(uow.session.identity_map), 0)
            self.assertEqual(
                connection.sync_connection.get_execution_options(), original_options
            )
            self.assertEqual(
                await connection.scalar(text("SHOW search_path")), original_path
            )
        async with UnitOfWork(self.sessions) as uow:
            user = await SqlAlchemyUserRepository(uow.session, self.naming).get_by_id(
                user_id, tenant_id=left
            )
            self.assertEqual(user.first_name, "Updated")

    async def test_email_foreign_key_cannot_reference_other_schema(self):
        left, right = await self.new_tenant_schema(), await self.new_tenant_schema()
        user = self.make_user(left)
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyUserRepository(uow.session, self.naming)
            await repository.add(user, tenant_id=left)
            self.assertIsNone(await repository.get_by_id(user.id, tenant_id=right))
            self.assertFalse(
                await repository.exists_by_tenant_and_email(right, "shared@example.com")
            )
            with self.assertRaises(IntegrityError):
                async with uow.session.begin_nested():
                    await uow.session.execute(
                        insert(UserEmailModel.__table__)
                        .values(
                            id=uuid4(),
                            user_id=user.id.uuid,
                            email="foreign@example.com",
                        )
                        .execution_options(
                            schema_translate_map={
                                "tenant": self.naming.schema_name(right)
                            }
                        )
                    )
            with self.assertRaises(IntegrityError):
                async with uow.session.begin_nested():
                    await uow.session.execute(
                        delete(UserModel.__table__)
                        .where(UserModel.__table__.c.id == user.id.uuid)
                        .execution_options(
                            schema_translate_map={
                                "tenant": self.naming.schema_name(left)
                            }
                        )
                    )

    async def test_upgrade_from_warehouses_and_identity_downgrade(self):
        tenant_id = await self.new_tenant_schema()
        schema = self.naming.schema_name(tenant_id)
        async with self.engine.begin() as connection:
            await self.migrator.downgrade(connection, schema, "0001_warehouses")
            self.assertEqual(
                await self.migrator.current(connection, schema), ("0001_warehouses",)
            )
            self.assertFalse(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table("users", schema=schema)
                )
            )
            await self.migrator.upgrade(connection, schema)
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await self.migrator.current(connection, schema),
                ("0002_identity_users",),
            )
            foreign_keys = await connection.run_sync(
                lambda conn: inspect(conn).get_foreign_keys(
                    "user_emails", schema=schema
                )
            )
            self.assertEqual(foreign_keys[0]["referred_schema"], schema)
            self.assertEqual(foreign_keys[0]["referred_table"], "users")
            self.assertTrue(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table("warehouses", schema=schema)
                )
            )

    async def test_missing_schema_and_missing_tables_fail_without_fallback(self):
        missing = EntityIdVO.from_value(uuid4())
        empty = await self.new_tenant_schema()
        async with self.engine.begin() as connection:
            await self.migrator.downgrade(
                connection, self.naming.schema_name(empty), "0001_warehouses"
            )
        for tenant_id in (missing, empty):
            with self.assertRaises(ProgrammingError) as raised:
                async with UnitOfWork(self.sessions) as uow:
                    await SqlAlchemyUserRepository(uow.session, self.naming).get_by_id(
                        UserIdVO.from_value(uuid4()), tenant_id=tenant_id
                    )
            self.assertIn(
                self.naming.schema_name(tenant_id), raised.exception.statement
            )

    async def test_admin_failure_rolls_back_schema_and_global_records(self):
        with self.assertRaisesRegex(RuntimeError, "Injected admin failure"):
            await self.onboard("fail", fail_admin=True)
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                self.assertFalse(await schema_exists(connection, schema))
            self.assertIsNone(
                await connection.scalar(
                    select(TenantModel.id).where(TenantModel.id.in_(self.tenant_ids))
                )
            )
            self.assertIsNone(
                await connection.scalar(
                    select(TenantDomainModel.id).where(
                        TenantDomainModel.tenant_id.in_(self.tenant_ids)
                    )
                )
            )

    async def test_http_login_profile_isolation_and_logout_with_real_di(self):
        left, right = await self.onboard("left"), await self.onboard("right")
        tokens, mail = _MemoryTokens(), AsyncMock()
        app = FastAPI()
        app.state.db = self.sessions
        app.include_router(auth_router, prefix="/api/console")
        app.dependency_overrides[get_otp_challenge_store] = lambda: tokens
        app.dependency_overrides[get_session_store] = lambda: tokens
        app.dependency_overrides[get_email_service] = lambda: mail
        endpoint = "/api/console/auth"
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://{left.tenant_domain_host}",
        ) as client:
            response = await client.post(
                f"{endpoint}/request-otp", json={"email": "shared@example.com"}
            )
            self.assertEqual(response.status_code, 200, response.text)
            token = response.json()["token"]
            code = mail.send.await_args.args[2]["otp_code"]
            payload = {"email": "shared@example.com", "token": token, "code": code}
            response = await client.post(
                f"http://{right.tenant_domain_host}{endpoint}/confirm-otp", json=payload
            )
            self.assertEqual(response.status_code, 401, response.text)
            response = await client.post(f"{endpoint}/confirm-otp", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["user_id"], str(left.user_id))
            self.assertEqual(response.json()["tenant_id"], str(left.tenant_id))
            cookie = client.cookies.get(dnk_config.AUTH.session_cookie_name)
            self.assertTrue(cookie)
            response = await client.get(f"{endpoint}/me")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["emails"][0]["is_verified"])
            profile = {
                "last_name": "Tester",
                "first_name": "Updated",
                "middle_name": None,
                "interface_language": "en",
                "interface_theme": "dark",
                "timezone": "Europe/Warsaw",
            }
            response = await client.patch(f"{endpoint}/me", json=profile)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["first_name"], "Updated")
            foreign_url = f"http://{right.tenant_domain_host}{endpoint}/me"
            headers = {"cookie": f"{dnk_config.AUTH.session_cookie_name}={cookie}"}
            self.assertEqual(
                (await client.get(foreign_url, headers=headers)).status_code, 401
            )
            self.assertEqual(
                (
                    await client.patch(foreign_url, headers=headers, json=profile)
                ).status_code,
                401,
            )
            response = await client.post(f"{endpoint}/logout")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                (await client.get(f"{endpoint}/me", headers=headers)).status_code, 401
            )
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyUserRepository(uow.session, self.naming)
            user = await repository.get_by_id(
                UserIdVO.from_value(left.user_id),
                tenant_id=EntityIdVO.from_value(left.tenant_id),
            )
            self.assertEqual(user.first_name, "Updated")
            other = await repository.get_by_id(
                UserIdVO.from_value(right.user_id),
                tenant_id=EntityIdVO.from_value(right.tenant_id),
            )
            self.assertEqual(other.first_name, "Alice")
            self.assertFalse(other.emails[0].is_verified)
