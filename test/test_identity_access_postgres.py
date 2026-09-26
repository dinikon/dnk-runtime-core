"""Real tenant migrations, invitation concurrency and access/session revocation."""

import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.access_service import IdentityAccessService
from src.modules.identity.application.cloud_auth_service import CloudAuthService
from src.modules.identity.application.ports.cloud import CloudConnection
from src.modules.identity.application.auth.service import OtpService, SessionService
from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.domain.user import User
from src.modules.identity.infrastructure.repository.access_repository import (
    AccessRepository,
)
from src.modules.identity.infrastructure.repository.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.adapter.session_store import (
    TokenManagerBackedSessionStore,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.email import SystemEmailKind
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend
from modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import UnitOfWork
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class IdentityAccessPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant = EntityIdVO.from_value(uuid4())
        self.naming = TenantSchemaNaming("identity_")
        self.schema = self.naming.schema_name(self.tenant)
        self.context = SimpleNamespace(
            tenant_id=self.tenant.uuid, tenant_domain_id=uuid4(), host="tenant.example"
        )
        self.reader = AsyncMock()
        self.reader.get_by_host.return_value = self.context
        self.tokens = TokenManager(InMemoryTokenBackend())
        self.session_store = TokenManagerBackedSessionStore(self.tokens)
        self.projections = AsyncMock()
        self.mail = AsyncMock()
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(self.schema))
            await TenantMigrator().upgrade(connection, self.schema)
        self.admin = User.create_tenant_admin(self.tenant, "Admin", "Owner")
        self.admin.add_email("admin@example.com", is_primary=True, is_verified=True)
        self.member = User.create_tenant_admin(self.tenant, "Local", "Member")
        self.member.role = "member"
        self.member.add_email("member@example.com", is_primary=True, is_verified=True)
        async with UnitOfWork(self.sessions) as uow:
            service = self.service(uow)
            await service.users.add(self.admin, tenant_id=self.tenant)
            await service.users.add(self.member, tenant_id=self.tenant)
            self.admin_session = await service.issue_session(self.context, self.admin)
            self.member_session = await service.issue_session(self.context, self.member)

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.execute(DropSchema(self.schema, cascade=True))
        await self.engine.dispose()

    def service(self, uow):
        return IdentityAccessService(
            uow=uow,
            users=SqlAlchemyUserRepository(uow.session, self.naming),
            access=AccessRepository(uow.session, self.naming),
            sessions=self.session_store,
            tenant_reader=self.reader,
            tokens=self.tokens,
            otp=OtpService(6),
            session_service=SessionService(),
            email=self.mail,
            settings=IdentityAuthSettings(),
            projections=self.projections,
        )

    async def test_revoke_reenable_never_resurrects_old_sessions_and_last_admin_guard(
        self,
    ):
        async with UnitOfWork(self.sessions) as uow:
            service = self.service(uow)
            with self.assertRaises(IdentityAccessError):
                await service.change_user(
                    "tenant.example",
                    self.member_session.token,
                    self.admin.id.uuid,
                    status="revoked",
                )
            with self.assertRaises(IdentityAccessError):
                await service.change_user(
                    "tenant.example",
                    self.admin_session.token,
                    self.admin.id.uuid,
                    role="member",
                )
            await service.change_user(
                "tenant.example",
                self.admin_session.token,
                self.member.id.uuid,
                status="revoked",
            )
            with self.assertRaises(IdentityAccessError):
                await service.principal("tenant.example", self.member_session.token)
            await service.change_user(
                "tenant.example",
                self.admin_session.token,
                self.member.id.uuid,
                status="active",
            )
            with self.assertRaises(IdentityAccessError):
                await service.principal("tenant.example", self.member_session.token)
            current = await service.users.get_by_id(
                self.member.id, tenant_id=self.tenant
            )
            session = await service.issue_session(self.context, current)
            self.assertEqual(
                (await service.principal("tenant.example", session.token))[1].id,
                self.member.id,
            )

    async def test_invitation_creates_only_after_one_time_otp_and_refuses_existing_account(
        self,
    ):
        async with UnitOfWork(self.sessions) as uow:
            service = self.service(uow)
            with self.assertRaises(IdentityAccessError):
                await service.invite(
                    "tenant.example",
                    self.admin_session.token,
                    "member@example.com",
                    "admin",
                )
            invite = await service.invite(
                "tenant.example",
                self.admin_session.token,
                "guest@example.com",
                "member",
            )
            self.mail.send.assert_awaited_once_with(
                SystemEmailKind.SEND_INVITATION,
                "guest@example.com",
                {"invitation_url": invite["invitation_url"]},
            )
            secret = parse_qs(urlsplit(invite["invitation_url"]).fragment)["token"][0]
            self.assertFalse(
                await service.users.exists_by_tenant_and_email(
                    self.tenant, "guest@example.com"
                )
            )
            otp = await service.request_invitation_otp("tenant.example", secret)
            self.assertEqual(self.mail.send.await_count, 2)
            self.assertEqual(self.mail.send.call_args.args[1], "guest@example.com")

        async def accept():
            try:
                async with UnitOfWork(self.sessions) as uow:
                    return await self.service(uow).accept_invitation(
                        "tenant.example",
                        secret,
                        otp["token"],
                        otp["code"],
                        "Guest",
                        "Person",
                    )
            except IdentityAccessError:
                return None

        results = await asyncio.gather(accept(), accept())
        self.assertEqual(sum(r is not None for r in results), 1)
        async with UnitOfWork(self.sessions) as uow:
            service = self.service(uow)
            users = await service.access.list_users(self.tenant.uuid)
            self.assertEqual(
                len([u for u in users if u["email"] == "guest@example.com"]), 1
            )
            self.assertEqual(len(users), 3)
            self.projections.set_available.assert_not_called()

    async def test_cloud_link_is_explicit_and_unlink_invalidates_session(self):
        core_tenant = uuid4()
        connection = CloudConnection(
            core_tenant,
            f"https://core.example/oidc/tenants/{core_tenant}",
            "client",
            "secret",
            "https://tenant.example/api/auth/cloud/callback/",
        )
        reader = AsyncMock()
        reader.get.return_value = connection
        oidc = AsyncMock()
        oidc.authorization_url.return_value = "https://core.example/authorize"
        oidc.exchange.return_value = str(uuid4())
        async with UnitOfWork(self.sessions) as uow:
            service = self.service(uow)
            cloud = CloudAuthService(service, reader, oidc)
            await cloud.start(
                "tenant.example", self.member_session.token, "browser", "link"
            )
            state_key = next(
                k for k in self.tokens._backend._storage if k.startswith("oidc_state:")
            )
            state = state_key.rsplit(":", 1)[1]
            with self.assertRaises(IdentityAccessError):
                await cloud.callback(
                    "tenant.example",
                    self.member_session.token,
                    "other-browser",
                    state=state,
                    code="code",
                    issuer=connection.issuer,
                )
            self.assertIsNone(
                await service.access.identity_for_user(
                    self.tenant.uuid, self.member.id.uuid
                )
            )
            await cloud.start(
                "tenant.example", self.member_session.token, "browser", "link"
            )
            state_key = next(
                k for k in self.tokens._backend._storage if k.startswith("oidc_state:")
            )
            state = state_key.rsplit(":", 1)[1]
            purpose, _ = await cloud.callback(
                "tenant.example",
                self.member_session.token,
                "browser",
                state=state,
                code="code",
                issuer=connection.issuer,
            )
            self.assertEqual(purpose, "link")
            with self.assertRaises(IdentityAccessError):
                await cloud.callback(
                    "tenant.example",
                    self.member_session.token,
                    "browser",
                    state=state,
                    code="code",
                    issuer=connection.issuer,
                )
            self.projections.set_available.assert_awaited_with(
                self.tenant.uuid,
                __import__("uuid").UUID(oidc.exchange.return_value),
                True,
                "member",
            )
            await cloud.unlink("tenant.example", self.member_session.token)
            self.assertIsNone(
                await service.access.identity_for_user(
                    self.tenant.uuid, self.member.id.uuid
                )
            )
            with self.assertRaises(IdentityAccessError):
                await service.principal("tenant.example", self.member_session.token)

    async def test_role_only_changes_publish_the_bound_users_current_role(self):
        subject = uuid4()
        async with UnitOfWork(self.sessions) as uow:
            service = self.service(uow)
            await service.access.bind(
                self.tenant.uuid,
                self.member.id.uuid,
                "https://core.example/issuer",
                str(subject),
            )
            await uow.commit()
            for role, status in (
                ("admin", "active"),
                ("member", "active"),
                ("member", "revoked"),
            ):
                await service.change_user(
                    "tenant.example",
                    self.admin_session.token,
                    self.member.id.uuid,
                    role=role,
                    status=status,
                )
                self.projections.set_available.assert_awaited_with(
                    self.tenant.uuid, subject, status == "active", role
                )
            self.assertEqual(self.projections.set_available.await_count, 3)

    async def test_http_callback_failure_rolls_back_binding_before_safe_redirect(self):
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from src.modules.identity.presentation.http.integration import cloud_router
        from src.modules.identity.presentation.depends.integration import (
            get_cloud_service,
        )

        core_tenant = uuid4()
        connection = CloudConnection(
            core_tenant,
            f"https://core.example/oidc/tenants/{core_tenant}",
            "client",
            "secret",
            "https://tenant.example/api/auth/cloud/callback/",
        )
        reader = AsyncMock()
        reader.get.return_value = connection
        oidc = AsyncMock()
        oidc.authorization_url.return_value = "https://core.example/authorize"
        oidc.exchange.return_value = str(uuid4())
        self.projections.set_available.side_effect = RuntimeError(
            "injected outbox write failure"
        )
        async with UnitOfWork(self.sessions) as uow:
            local = self.service(uow)
            cloud = CloudAuthService(local, reader, oidc)
            await cloud.start(
                "tenant.example", self.member_session.token, "browser", "link"
            )
            state = next(
                k.rsplit(":", 1)[1]
                for k in self.tokens._backend._storage
                if k.startswith("oidc_state:")
            )
            app = FastAPI()
            app.include_router(cloud_router)
            app.dependency_overrides[get_cloud_service] = lambda: cloud
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="https://tenant.example"
            ) as client:
                response = await client.get(
                    "/api/auth/cloud/callback/",
                    params={"state": state, "code": "code", "iss": connection.issuer},
                    headers={
                        "cookie": f"dnk_session={self.member_session.token}; dnk_auth_flow=browser"
                    },
                )
                self.assertEqual(response.status_code, 303)
                self.assertEqual(
                    response.headers["location"],
                    "/login?cloud_error=authorization_failed",
                )
            self.assertIsNone(
                await local.access.identity_for_user(
                    self.tenant.uuid, self.member.id.uuid
                )
            )
