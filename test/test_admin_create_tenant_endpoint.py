import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import dnk_config
from src.dnk_app import DnkApp
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.router import router as api_router
from src.modules.shared.db.base import Base
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class TenancyEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_control_plane_api_key = dnk_config.CONTROL_PLANE_API_KEY
        dnk_config.CONTROL_PLANE_API_KEY = "test-control-plane-key"

        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test.db"
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )
        asyncio.run(self._create_schema())

        self._app = DnkApp()
        self._app.include_router(api_router)
        self._app.state.db = self._session_factory

        self._client_context = TestClient(self._app)
        self.client = self._client_context.__enter__()

    def tearDown(self) -> None:
        self._client_context.__exit__(None, None, None)
        asyncio.run(self._engine.dispose())
        self._temp_dir.cleanup()
        dnk_config.CONTROL_PLANE_API_KEY = self._original_control_plane_api_key

    def test_create_tenant_requires_authorization(self) -> None:
        response = self.client.post(
            "/api/admin/create-tenant",
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized.")

    def test_create_tenant_rejects_invalid_api_key(self) -> None:
        response = self.client.post(
            "/api/admin/create-tenant",
            headers={"Authorization": "Bearer wrong-key"},
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized.")

    def test_create_tenant_persists_external_id(self) -> None:
        response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tenant_status"], "active")
        self.assertEqual(payload["user_status"], "active")
        self.assertEqual(payload["tenant_domain_host"], "acme.example.com")

        counts = asyncio.run(self._fetch_counts())
        self.assertEqual(counts, (1, 1, 1, 1))

        tenant = asyncio.run(self._get_tenant_by_external_id("tenant-acme"))
        self.assertIsNotNone(tenant)
        assert tenant is not None
        self.assertEqual(tenant.name, "Acme")
        self.assertEqual(tenant.external_id, "tenant-acme")

    def test_create_tenant_rejects_duplicate_external_id(self) -> None:
        first_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-shared",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Beta",
                external_id="tenant-shared",
                tenant_host="beta.example.com",
                email="jane.roe@example.com",
            ),
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.json()["detail"],
            "Tenant with external_id 'tenant-shared' already exists.",
        )

        counts = asyncio.run(self._fetch_counts())
        self.assertEqual(counts, (1, 1, 1, 1))

    def test_create_tenant_rejects_duplicate_host(self) -> None:
        first_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Beta",
                external_id="tenant-beta",
                tenant_host="acme.example.com",
                email="jane.roe@example.com",
            ),
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.json()["detail"],
            "Tenant domain host 'acme.example.com' already exists.",
        )

    def test_resolve_tenant_returns_active_tenant(self) -> None:
        create_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )
        self.assertEqual(create_response.status_code, 200)

        response = self.client.get(
            "/api/console/tenants/resolve",
            headers={"Host": "ACME.EXAMPLE.COM"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": True,
                "available": True,
                "status": "active",
                "tenant_id": create_response.json()["tenant_id"],
                "api_host": "acme.example.com",
            },
        )

    def test_resolve_tenant_returns_freeze_status(self) -> None:
        create_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )
        self.assertEqual(create_response.status_code, 200)

        tenant_id = create_response.json()["tenant_id"]
        asyncio.run(self._set_tenant_status(tenant_id, "freeze"))

        response = self.client.get(
            "/api/console/tenants/resolve",
            headers={"Host": "acme.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": True,
                "available": False,
                "status": "freeze",
                "tenant_id": tenant_id,
                "api_host": "acme.example.com",
            },
        )

    def test_resolve_tenant_ignores_domains_with_deleted_status(self) -> None:
        create_response = self.client.post(
            "/api/admin/create-tenant",
            headers=self._auth_headers(),
            json=self._create_payload(
                tenant_name="Acme",
                external_id="tenant-acme",
                tenant_host="acme.example.com",
                email="john.doe@example.com",
            ),
        )
        self.assertEqual(create_response.status_code, 200)

        asyncio.run(self._mark_domain_deleted("acme.example.com"))

        response = self.client.get(
            "/api/console/tenants/resolve",
            headers={"Host": "acme.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": False,
                "available": False,
                "status": "not_found",
                "tenant_id": None,
                "api_host": None,
            },
        )

    def test_resolve_tenant_returns_not_found_for_unknown_host(self) -> None:
        response = self.client.get(
            "/api/console/tenants/resolve",
            headers={"Host": "missing.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": False,
                "available": False,
                "status": "not_found",
                "tenant_id": None,
                "api_host": None,
            },
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {dnk_config.CONTROL_PLANE_API_KEY}"}

    @staticmethod
    def _create_payload(
        *,
        tenant_name: str,
        external_id: str,
        tenant_host: str,
        email: str,
    ) -> dict[str, object]:
        return {
            "tenant": {
                "name": tenant_name,
                "external_id": external_id,
            },
            "tenant_domain": {"host": tenant_host},
            "user": {"first_name": "John", "last_name": "Doe"},
            "user_email": {"email": email},
        }

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

    async def _get_tenant_by_external_id(self, external_id: str) -> TenantModel | None:
        async with self._session_factory() as session:
            return await session.scalar(
                select(TenantModel).where(TenantModel.external_id == external_id)
            )

    async def _set_tenant_status(self, tenant_id: str, status: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(TenantModel)
                .where(TenantModel.id == tenant_id)
                .values(status=status)
            )
            await session.commit()

    async def _mark_domain_deleted(self, host: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(TenantDomainModel)
                .where(TenantDomainModel.host == host)
                .values(status="deleted")
            )
            await session.commit()
