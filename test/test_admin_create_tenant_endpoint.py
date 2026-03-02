import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.common.db.base import Base
from src.dnk_app import DnkApp
from src.infrastructure.persistence.tenant import TenantModel
from src.infrastructure.persistence.tenant_domain import TenantDomainModel
from src.infrastructure.persistence.user import UserModel
from src.infrastructure.persistence.user_email import UserEmailModel
from src.presentation.api.admin_tenants import router as admin_tenants_router


class AdminCreateTenantEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test.db"
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )
        asyncio.run(self._create_schema())

        self._app = DnkApp()
        self._app.include_router(admin_tenants_router)
        self._app.state.db = self._session_factory

        self._client_context = TestClient(self._app)
        self.client = self._client_context.__enter__()

    def tearDown(self) -> None:
        self._client_context.__exit__(None, None, None)
        asyncio.run(self._engine.dispose())
        self._temp_dir.cleanup()

    def test_create_tenant_creates_all_entities(self) -> None:
        response = self.client.post(
            "/api/admin/create-tenant",
            json={
                "tenant": {"name": "Acme"},
                "tenant_domain": {"host": "acme.example.com"},
                "user": {"first_name": "John", "last_name": "Doe"},
                "user_email": {"email": "john.doe@example.com"},
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tenant_status"], "active")
        self.assertEqual(payload["user_status"], "active")
        self.assertEqual(payload["tenant_domain_host"], "acme.example.com")

        counts = asyncio.run(self._fetch_counts())
        self.assertEqual(counts, (1, 1, 1, 1))

    def test_create_tenant_rolls_back_when_email_conflicts(self) -> None:
        first_response = self.client.post(
            "/api/admin/create-tenant",
            json={
                "tenant": {"name": "Acme"},
                "tenant_domain": {"host": "acme.example.com"},
                "user": {"first_name": "John", "last_name": "Doe"},
                "user_email": {"email": "john.doe@example.com"},
            },
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            "/api/admin/create-tenant",
            json={
                "tenant": {"name": "Beta"},
                "tenant_domain": {"host": "acme.example.com"},
                "user": {"first_name": "Jane", "last_name": "Roe"},
                "user_email": {"email": "john.doe@example.com"},
            },
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.json()["detail"],
            "Tenant domain host 'acme.example.com' already exists.",
        )

        counts = asyncio.run(self._fetch_counts())
        self.assertEqual(counts, (1, 1, 1, 1))

    def test_create_tenant_allows_same_email_in_different_tenants(self) -> None:
        first_response = self.client.post(
            "/api/admin/create-tenant",
            json={
                "tenant": {"name": "Acme"},
                "tenant_domain": {"host": "acme.example.com"},
                "user": {"first_name": "John", "last_name": "Doe"},
                "user_email": {"email": "john.doe@example.com"},
            },
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            "/api/admin/create-tenant",
            json={
                "tenant": {"name": "Beta"},
                "tenant_domain": {"host": "beta.example.com"},
                "user": {"first_name": "Jane", "last_name": "Roe"},
                "user_email": {"email": "john.doe@example.com"},
            },
        )

        self.assertEqual(second_response.status_code, 200)

        counts = asyncio.run(self._fetch_counts())
        self.assertEqual(counts, (2, 2, 2, 2))

    async def _create_schema(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def _fetch_counts(self) -> tuple[int, int, int, int]:
        async with self._session_factory() as session:
            tenant_count = await session.scalar(
                select(func.count()).select_from(TenantModel)
            )
            user_count = await session.scalar(
                select(func.count()).select_from(UserModel)
            )
            email_count = await session.scalar(
                select(func.count()).select_from(UserEmailModel)
            )
            domain_count = await session.scalar(
                select(func.count()).select_from(TenantDomainModel)
            )
            return tenant_count, user_count, email_count, domain_count
