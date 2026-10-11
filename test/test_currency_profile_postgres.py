"""Tenant-миграции, транзакции профиля и HTTP с реальным DI в временных базах."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import dnk_config
from src.modules.identity.application.auth.port.session_store import SessionRecord
from src.modules.identity.application.user.command.update_current_user_profile.command import (
    UpdateCurrentUserProfileCommand,
)
from src.modules.identity.application.user.command.update_current_user_profile.handler import (
    UpdateCurrentUserProfileHandler,
)
from src.modules.identity.application.user.query.get_current_user.query import (
    GetCurrentUserQuery,
)
from src.modules.identity.application.user.query.get_current_user.handler import (
    GetCurrentUserHandler,
)
from src.modules.identity.domain.user.entity import User
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.identity.infrastructure.user.persistence.repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.user.persistence.query_repository import (
    SqlAlchemyUserProfileQueryRepository,
)
from src.modules.identity.infrastructure.user.currency_validator import (
    ReferenceDataProfileCurrencyValidator,
)
from src.modules.identity.infrastructure.user.tenant_currency_settings import (
    TenancyProfileCurrencySettingsAdapter,
)
from src.modules.identity.presentation.auth.http.router import router
from src.modules.identity.presentation.auth.http.csrf_router import (
    router as csrf_router,
)
from src.modules.identity.presentation.auth.providers import get_session_store
from src.modules.identity.presentation.user.depends import (
    get_profile_currency_validator,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.handler import (
    GetTenantCurrencySettingsHandler,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.query_repository import (
    SqlAlchemyTenantCurrencySettingsQueryRepository,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.presentation.tenant.http.tenant_gate import (
    TenantAdmissionMiddleware,
)
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from test.test_currency_profile import PROFILE


class CurrencyProfilePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        value = os.environ.get("DNK_TEST_DATABASE_URL")
        if not value:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is required for disposable PostgreSQL databases"
            )
        url = make_url(value).set(drivername="postgresql+asyncpg")
        self.name = "dnk_currency_profile_test_" + uuid4().hex
        self.admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with self.admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.name}"'))
        self.engine = create_async_engine(url.set(database=self.name))
        self.addAsyncCleanup(self.drop_database)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming("dnk_")
        self.tenants = tuple(EntityIdVO.from_value(uuid4()) for _ in range(2))
        self.user_id = UserIdVO.from_value(uuid4())
        self.domains = tuple(uuid4() for _ in range(2))
        self.schema = self.naming.schema_name(self.tenants[0])
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            await connection.execute(
                text(
                    "INSERT INTO public.ref_currencies (code,numeric_code,name,minor_units,active) VALUES ('USD','840','Dollar',2,true),('UAH','980','Hryvnia',2,true),('JPY','392','Yen',0,false),('XAU','959','Gold',NULL,true)"
                )
            )
            for index, tenant in enumerate(self.tenants):
                schema = self.naming.schema_name(tenant)
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await TenantMigrator().upgrade(connection, schema)
                await connection.execute(
                    insert(TenantModel.__table__).values(
                        id=tenant.uuid,
                        name="Profile test",
                        external_id=str(tenant.uuid),
                        status="active",
                    )
                )
                await connection.execute(
                    insert(TenantDomainModel.__table__).values(
                        id=self.domains[index],
                        tenant_id=tenant.uuid,
                        service_type="console",
                        kind="custom",
                        host=f"profile{index}.example",
                        status="active",
                        auth_mode="local",
                        is_primary=True,
                        verification_status="verified",
                    )
                )
            await connection.execute(
                text(
                    f"UPDATE \"{self.schema}\".tenant_currency_settings SET base_currency='USD'"
                )
            )
        for tenant in self.tenants:
            async with self.uow(tenant) as uow:
                user = replace(
                    User.create_tenant_admin(tenant, "Alice", "Tester"), id=self.user_id
                )
                user.add_email("alice@example.com", is_primary=True, is_verified=True)
                await SqlAlchemyUserRepository(uow.session, self.naming).add(
                    user, tenant_id=tenant
                )

    async def drop_database(self) -> None:
        await self.engine.dispose()
        async with self.admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{self.name}"'))
        await self.admin.dispose()

    @asynccontextmanager
    async def uow(self, tenant=None):
        tenant = tenant or self.tenants[0]
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant.uuid, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow

    def settings(self, session, tenant):
        return TenancyProfileCurrencySettingsAdapter(
            GetTenantCurrencySettingsHandler(
                SqlAlchemyTenantCurrencySettingsQueryRepository(
                    session, TenantIdVO.from_value(tenant.uuid)
                )
            )
        )

    def update_handler(self, session, tenant):
        return UpdateCurrentUserProfileHandler(
            SqlAlchemyUserRepository(session, self.naming),
            ReferenceDataProfileCurrencyValidator(
                ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(session))
            ),
            self.settings(session, tenant),
        )

    def command(self, tenant=None, **changes):
        return UpdateCurrentUserProfileCommand(
            tenant_id=tenant or self.tenants[0],
            user_id=self.user_id,
            **PROFILE,
            **changes,
        )

    async def read(self, tenant=None):
        tenant = tenant or self.tenants[0]
        async with self.uow(tenant) as uow:
            return await GetCurrentUserHandler(
                SqlAlchemyUserProfileQueryRepository(uow.session, self.naming),
                self.settings(uow.session, tenant),
            ).execute(GetCurrentUserQuery(tenant, self.user_id))

    async def update(self, tenant=None, **changes):
        tenant = tenant or self.tenants[0]
        async with self.uow(tenant) as uow:
            return await self.update_handler(uow.session, tenant).execute(
                self.command(tenant, **changes)
            )

    async def test_column_is_local_nullable_and_migration_roundtrip_preserves_users(
        self,
    ) -> None:
        async with self.engine.begin() as connection:
            self.assertIsNone(
                await connection.scalar(text("SELECT to_regclass('public.users')"))
            )
            columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("users", schema=self.schema)
            )
            column = next(
                item for item in columns if item["name"] == "display_currency"
            )
            self.assertTrue(column["nullable"])
            self.assertEqual(column["type"].length, 3)
            await TenantMigrator().downgrade(
                connection, self.schema, "0024_currency_exchange_rates"
            )
            await TenantMigrator().upgrade(connection, self.schema)
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{self.schema}".users')
                ),
                1,
            )
            self.assertIsNone(
                await connection.scalar(
                    text(f'SELECT display_currency FROM "{self.schema}".users')
                )
            )
            self.assertEqual(
                await TenantMigrator().current(connection, self.schema),
                ("0025_user_display_currency",),
            )

    async def test_normalization_roundtrip_omission_reset_and_identical_ids_are_isolated(
        self,
    ) -> None:
        self.assertEqual((await self.read()).effective_display_currency, "USD")
        self.assertEqual(
            (await self.read(self.tenants[1])).effective_display_currency, "UAH"
        )
        await self.update(display_currency=" uah ", display_currency_provided=True)
        self.assertEqual((await self.read()).display_currency, "UAH")
        self.assertIsNone((await self.read(self.tenants[1])).display_currency)
        await self.update()
        self.assertEqual((await self.read()).display_currency, "UAH")
        await self.update(display_currency_provided=True)
        self.assertIsNone((await self.read()).display_currency)
        self.assertEqual((await self.read()).effective_display_currency, "USD")
        async with self.uow() as uow:
            with self.assertRaisesRegex(RuntimeError, "not bound"):
                await SqlAlchemyUserRepository(uow.session, self.naming).get_by_id(
                    self.user_id, tenant_id=self.tenants[1]
                )

    async def test_unknown_inactive_rejected_and_all_active_codes_allowed(self) -> None:
        for code in ("ZZZ", "JPY"):
            with self.assertRaises(CurrencyCodeNotSupportedError):
                await self.update(display_currency=code, display_currency_provided=True)
        self.assertIsNone((await self.read()).display_currency)
        await self.update(display_currency="XAU", display_currency_provided=True)
        self.assertEqual((await self.read()).display_currency, "XAU")

    async def test_write_failure_and_commit_failure_roll_back(self) -> None:
        real_update = SqlAlchemyUserRepository.update_profile

        async def fail_after_write(repository, user, **kwargs):
            await real_update(repository, user, **kwargs)
            raise RuntimeError("Injected failure after SQL")

        with (
            patch.object(SqlAlchemyUserRepository, "update_profile", fail_after_write),
            self.assertRaises(RuntimeError),
        ):
            await self.update(display_currency="UAH", display_currency_provided=True)
        self.assertIsNone((await self.read()).display_currency)
        with (
            patch.object(
                UnitOfWork, "commit", side_effect=RuntimeError("commit failed")
            ),
            self.assertRaises(RuntimeError),
        ):
            await self.update(display_currency="UAH", display_currency_provided=True)
        self.assertIsNone((await self.read()).display_currency)

    async def test_concurrent_omitted_currency_preserves_committed_choice(self) -> None:
        entered, release = asyncio.Event(), asyncio.Event()
        real_update = SqlAlchemyUserRepository.update_profile

        async def pause(repository, user, **kwargs):
            await real_update(repository, user, **kwargs)
            entered.set()
            await release.wait()

        with patch.object(SqlAlchemyUserRepository, "update_profile", pause):
            first = asyncio.create_task(
                self.update(display_currency="UAH", display_currency_provided=True)
            )
            second = None
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                second = asyncio.create_task(self.update())
                done, _ = await asyncio.wait({second}, timeout=0.1)
                self.assertFalse(done)
                release.set()
                await asyncio.wait_for(asyncio.gather(first, second), timeout=5)
            finally:
                release.set()
                for task in (first, second):
                    if task is not None:
                        task.cancel()
                await asyncio.gather(
                    *(task for task in (first, second) if task is not None),
                    return_exceptions=True,
                )
        self.assertEqual((await self.read()).display_currency, "UAH")

    async def test_query_uses_single_snapshot_without_restoring_aggregate(self) -> None:
        with patch.object(
            User, "restore", side_effect=AssertionError("Read must use projection")
        ):
            result = await self.read()
        self.assertEqual(result.emails[0].email, "alice@example.com")
        async with self.uow() as uow:
            await uow.session.execute(
                text(f'UPDATE "{self.schema}".user_emails SET is_deleted=true')
            )
        self.assertEqual((await self.read()).emails, [])

    async def test_http_real_auth_di_csrf_tenant_isolation_and_commit_error(
        self,
    ) -> None:
        app = FastAPI()
        app.state.db = self.sessions
        app.state.token_manager = TokenManager(InMemoryTokenBackend())
        app.add_middleware(TenantAdmissionMiddleware)
        app.include_router(router, prefix="/api/console")
        app.include_router(csrf_router)
        now = datetime.now(UTC)
        store = AsyncMock()
        session = SessionRecord(
            token="profile-session",
            session_id="profile-session",
            user_id=self.user_id.uuid,
            tenant_id=self.tenants[0].uuid,
            tenant_domain_id=self.domains[0],
            host="profile0.example",
            issued_at=now,
            expires_at=now + timedelta(hours=1),
        )
        store.get_session.side_effect = lambda tenant_id, token: (
            session
            if tenant_id == session.tenant_id and token == session.token
            else None
        )
        app.dependency_overrides[get_session_store] = lambda: store
        with (
            patch.object(dnk_config, "SCHEMA_PREFIX", "dnk_"),
            patch.object(dnk_config.AUTH, "allow_insecure_http", False),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="https://profile0.example",
            ) as client:
                endpoint = "/api/console/auth/me"
                self.assertEqual((await client.get(endpoint)).status_code, 401)
                client.cookies.set(
                    dnk_config.AUTH.session_cookie_name,
                    session.token,
                    domain="profile0.example",
                    path="/",
                )
                response = await client.get(endpoint)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["effective_display_currency"], "USD")
                self.assertEqual(
                    (await client.patch(endpoint, json=PROFILE)).status_code, 403
                )
                token_response = await client.get("/api/console/auth/csrf")
                self.assertEqual(token_response.status_code, 200, token_response.text)
                headers = {
                    "Origin": "https://profile0.example",
                    "X-CSRF-Token": token_response.json()["csrf_token"],
                }
                response = await client.patch(
                    endpoint,
                    json={**PROFILE, "display_currency": "uah"},
                    headers=headers,
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["display_currency"], "UAH")
                self.assertEqual(
                    (
                        await client.get(
                            f"https://profile1.example{endpoint}",
                            headers={
                                "Cookie": f"{dnk_config.AUTH.session_cookie_name}={session.token}"
                            },
                        )
                    ).status_code,
                    401,
                )
                with patch.object(
                    UnitOfWork, "commit", side_effect=RuntimeError("commit failed")
                ):
                    response = await client.patch(
                        endpoint,
                        json={**PROFILE, "display_currency": "USD"},
                        headers=headers,
                    )
                    self.assertEqual(response.status_code, 500, response.text)
                self.assertEqual(
                    (await client.get(endpoint)).json()["display_currency"], "UAH"
                )
        self.assertIsNone((await self.read(self.tenants[1])).display_currency)
