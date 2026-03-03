import asyncio
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import dnk_config
from src.dnk_app import DnkApp
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.identity.presentation.depends.auth_services import InMemoryEmailSender
from src.modules.router import router as api_router
from src.modules.shared.db.base import Base
from src.modules.shared.tokens import InMemoryTokenBackend, TokenManager
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


class ConsoleAuthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_control_plane_api_key = dnk_config.CONTROL_PLANE_API_KEY
        self._original_auth_settings = dnk_config.AUTH.model_copy(deep=True)

        dnk_config.CONTROL_PLANE_API_KEY = "test-control-plane-key"
        dnk_config.AUTH.otp_code_length = 6
        dnk_config.AUTH.otp_token_ttl_seconds = 300
        dnk_config.AUTH.session_ttl_seconds = 3600
        dnk_config.AUTH.session_cookie_name = "dnk_session"

        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "auth.db"
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )
        asyncio.run(self._create_schema())

        self.token_backend = InMemoryTokenBackend()
        self.token_manager = TokenManager(self.token_backend)
        self.email_sender = InMemoryEmailSender()

        self._app = DnkApp()
        self._app.include_router(api_router)
        self._app.state.db = self._session_factory
        self._app.state.token_manager = self.token_manager
        self._app.state.email_sender = self.email_sender

        self._client_context = TestClient(self._app)
        self.client = self._client_context.__enter__()

    def tearDown(self) -> None:
        self._client_context.__exit__(None, None, None)
        asyncio.run(self._engine.dispose())
        self._temp_dir.cleanup()
        dnk_config.CONTROL_PLANE_API_KEY = self._original_control_plane_api_key
        dnk_config.AUTH = self._original_auth_settings

    def test_request_otp_success_for_active_tenant_and_primary_email(self) -> None:
        tenant = self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("token", payload)
        self.assertEqual(payload["expires_in"], 300)
        self.assertNotIn("code", payload)

        stored = asyncio.run(
            self.token_manager.get_token(
                prefix="otp_login",
                suffix=tenant["tenant_id"],
                token=payload["token"],
            )
        )
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["email"], "john@example.com")
        self.assertEqual(len(self.email_sender.sent_codes), 1)
        self.assertEqual(self.email_sender.sent_codes[0].email, "john@example.com")

    def test_request_otp_returns_404_when_host_not_found(self) -> None:
        response = self.client.post(
            "http://missing.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )

        self.assertEqual(response.status_code, 404)

    def test_request_otp_searches_email_only_within_current_tenant(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="shared@example.com",
        )
        self._create_tenant(
            host="beta.example.com",
            external_id="tenant-beta",
            email="other@example.com",
        )

        response = self.client.post(
            "http://beta.example.com/api/console/auth/request-otp",
            json={"email": "shared@example.com"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(self.email_sender.sent_codes), 0)

    def test_request_otp_rejects_non_primary_email(self) -> None:
        tenant = self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        asyncio.run(
            self._add_secondary_email(
                user_id=tenant["user_id"],
                email="secondary@example.com",
            )
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "secondary@example.com"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(self.email_sender.sent_codes), 0)

    def test_confirm_otp_success_creates_session_and_cookie(self) -> None:
        tenant = self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        otp_response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )
        token = otp_response.json()["token"]
        code = self.email_sender.sent_codes[-1].code

        response = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json={
                "email": "john@example.com",
                "token": token,
                "code": code,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["tenant_id"], tenant["tenant_id"])

        session_token = response.cookies.get(dnk_config.AUTH.session_cookie_name)
        self.assertIsNotNone(session_token)
        assert session_token is not None
        stored_session = asyncio.run(
            self.token_manager.get_token(
                prefix="session",
                suffix=tenant["tenant_id"],
                token=session_token,
            )
        )
        self.assertIsNotNone(stored_session)

        stored_otp = asyncio.run(
            self.token_manager.get_token(
                prefix="otp_login",
                suffix=tenant["tenant_id"],
                token=token,
            )
        )
        self.assertIsNone(stored_otp)
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_confirm_otp_rejects_invalid_code(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        otp_response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json={
                "email": "john@example.com",
                "token": otp_response.json()["token"],
                "code": "000000",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_confirm_otp_rejects_invalid_token(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json={
                "email": "john@example.com",
                "token": "otp_missing",
                "code": "123456",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_confirm_otp_rejects_expired_otp(self) -> None:
        tenant = self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        otp_response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )
        token = otp_response.json()["token"]
        storage_key = f"otp_login:{tenant['tenant_id']}:{token}"
        self.token_backend._storage[storage_key].expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)

        response = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json={
                "email": "john@example.com",
                "token": token,
                "code": self.email_sender.sent_codes[-1].code,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_confirm_otp_rejects_email_mismatch(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        otp_response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json={
                "email": "other@example.com",
                "token": otp_response.json()["token"],
                "code": self.email_sender.sent_codes[-1].code,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_confirm_otp_rejects_host_mismatch(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="shared@example.com",
        )
        self._create_tenant(
            host="beta.example.com",
            external_id="tenant-beta",
            email="shared@example.com",
        )
        otp_response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "shared@example.com"},
        )

        response = self.client.post(
            "http://beta.example.com/api/console/auth/confirm-otp",
            json={
                "email": "shared@example.com",
                "token": otp_response.json()["token"],
                "code": self.email_sender.sent_codes[-1].code,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_confirm_otp_cannot_be_used_twice(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        otp_response = self.client.post(
            "http://acme.example.com/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )
        payload = {
            "email": "john@example.com",
            "token": otp_response.json()["token"],
            "code": self.email_sender.sent_codes[-1].code,
        }

        first = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json=payload,
        )
        second = self.client.post(
            "http://acme.example.com/api/console/auth/confirm-otp",
            json=payload,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 401)

    def test_logout_invalidates_session_and_clears_cookie(self) -> None:
        tenant = self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )
        session_token = self._confirm_login(
            host="acme.example.com",
            email="john@example.com",
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/logout",
            headers={
                "Cookie": (f"{dnk_config.AUTH.session_cookie_name}={session_token}"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        stored_session = asyncio.run(
            self.token_manager.get_token(
                prefix="session",
                suffix=tenant["tenant_id"],
                token=session_token,
            )
        )
        self.assertIsNone(stored_session)

    def test_logout_is_idempotent_for_missing_session(self) -> None:
        self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="john@example.com",
        )

        response = self.client.post(
            "http://acme.example.com/api/console/auth/logout",
            headers={
                "Cookie": (f"{dnk_config.AUTH.session_cookie_name}=sess_missing"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_logout_does_not_invalidate_session_of_other_tenant(self) -> None:
        acme = self._create_tenant(
            host="acme.example.com",
            external_id="tenant-acme",
            email="shared@example.com",
        )
        self._create_tenant(
            host="beta.example.com",
            external_id="tenant-beta",
            email="shared@example.com",
        )
        session_token = self._confirm_login(
            host="acme.example.com",
            email="shared@example.com",
        )

        response = self.client.post(
            "http://beta.example.com/api/console/auth/logout",
            headers={
                "Cookie": (f"{dnk_config.AUTH.session_cookie_name}={session_token}"),
            },
        )

        self.assertEqual(response.status_code, 200)
        stored_session = asyncio.run(
            self.token_manager.get_token(
                prefix="session",
                suffix=acme["tenant_id"],
                token=session_token,
            )
        )
        self.assertIsNotNone(stored_session)

    def _confirm_login(self, *, host: str, email: str) -> str:
        otp_response = self.client.post(
            f"http://{host}/api/console/auth/request-otp",
            json={"email": email},
        )
        response = self.client.post(
            f"http://{host}/api/console/auth/confirm-otp",
            json={
                "email": email,
                "token": otp_response.json()["token"],
                "code": self.email_sender.sent_codes[-1].code,
            },
        )
        self.assertEqual(response.status_code, 200)
        session_token = response.cookies.get(dnk_config.AUTH.session_cookie_name)
        assert session_token is not None
        return session_token

    def _create_tenant(
        self,
        *,
        host: str,
        external_id: str,
        email: str,
    ) -> dict[str, str]:
        response = self.client.post(
            "/api/admin/create-tenant",
            headers={
                "Authorization": f"Bearer {dnk_config.CONTROL_PLANE_API_KEY}",
            },
            json={
                "tenant": {"name": external_id.title(), "external_id": external_id},
                "tenant_domain": {"host": host},
                "user": {"first_name": "John", "last_name": "Doe"},
                "user_email": {"email": email},
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def _add_secondary_email(self, *, user_id: str, email: str) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                insert(UserEmailModel).values(
                    id=uuid4(),
                    user_id=user_id,
                    email=email,
                    is_primary=False,
                    is_verified=False,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

    async def _create_schema(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
