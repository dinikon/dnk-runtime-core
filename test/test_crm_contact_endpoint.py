from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import src.modules.persistence  # noqa: F401
from src.dnk_app import DnkApp
from src.modules.router import router as api_router
from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
)
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.runtime_schema.infrastructure.persistence.models import (
    ObjectMetadataModel,
)
from src.modules.shared.db.base import Base
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class TestCrmContactEndpoint(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.app = DnkApp()
        self.app.include_router(api_router)
        self.app.state.db = self.session_factory

        self.tenant_id = uuid4()
        self.data_source_id = uuid4()
        self.schema = "tenant_test"
        self.host = "acme.local"
        self.contact_id = uuid4()

        await self._seed_data()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def _seed_data(self) -> None:
        async with self.session_factory() as session:
            session.add(
                TenantModel(
                    id=self.tenant_id,
                    name="Acme",
                    external_id="acme-ext",
                    status="active",
                    custom_config=None,
                )
            )
            session.add(
                TenantDomainModel(
                    id=uuid4(),
                    tenant_id=self.tenant_id,
                    service_type="console",
                    kind="default",
                    host=self.host,
                    base_path=None,
                    auth_mode=None,
                    status="active",
                    is_primary=True,
                    is_wildcard=False,
                    parent_domain=None,
                    verification_status="verified",
                    tls_mode="managed",
                    metadata_json=None,
                )
            )
            session.add(
                TenantDataSourceModel(
                    id=self.data_source_id,
                    tenant_id=self.tenant_id,
                    type="sqlite",
                    is_remote=False,
                    dsn=None,
                    schema=self.schema,
                )
            )
            await session.flush()

            orchestrator = build_ddl_orchestrator(session=session)
            await orchestrator.sync_tenant_system_schema(
                SyncTenantSystemSchemaCommandDTO(
                    tenant_id=self.tenant_id,
                    data_source_id=self.data_source_id,
                    schema=self.schema,
                )
            )
            contact_object_id = await session.scalar(
                select(ObjectMetadataModel.id)
                .where(ObjectMetadataModel.tenant_id == str(self.tenant_id))
                .where(ObjectMetadataModel.data_source_id == str(self.data_source_id))
                .where(ObjectMetadataModel.name_singular == "contact")
                .limit(1)
            )
            assert contact_object_id is not None
            parsed_contact_object_id = (
                contact_object_id
                if isinstance(contact_object_id, UUID)
                else UUID(str(contact_object_id))
            )

            await orchestrator.create_field_definition(
                CreateFieldCommandDTO(
                    tenant_id=self.tenant_id,
                    object_id=parsed_contact_object_id,
                    schema=self.schema,
                    field_type="string",
                    field_name="nickname",
                    label="Nickname",
                    is_system=False,
                    is_custom=True,
                    is_nullable=True,
                )
            )

            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__contacts" '
                    '("id", "name_first_name", "name_last_name", "name_middle_name", "nickname") '
                    "VALUES (:id, :first_name, :last_name, :middle_name, :nickname)"
                ),
                {
                    "id": str(self.contact_id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "middle_name": "Michael",
                    "nickname": "JD",
                },
            )
            await session.commit()

    async def test_get_contact_endpoint_returns_contact(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url=f"http://{self.host}",
        ) as client:
            response = await client.get(f"/contacts/{self.contact_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.contact_id))
        self.assertEqual(payload["first_name"], "John")
        self.assertEqual(payload["last_name"], "Doe")
        self.assertEqual(payload["middle_name"], "Michael")
        self.assertEqual(payload["nickname"], "JD")
        self.assertNotIn("custom_fields", payload)

    async def test_get_contact_endpoint_returns_404_for_missing_record(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url=f"http://{self.host}",
        ) as client:
            response = await client.get(f"/contacts/{uuid4()}")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
