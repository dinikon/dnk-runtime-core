from __future__ import annotations

import unittest
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import src.modules.persistence  # noqa: F401
from src.dnk_app import DnkApp
from src.modules.router import router as api_router
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.shared.db.base import Base
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class TestCustomObjectEndpoint(unittest.IsolatedAsyncioTestCase):
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
            await session.commit()

    async def test_custom_object_end_to_end(self) -> None:
        request_record_id = uuid4()
        contact_id = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url=f"http://{self.host}",
        ) as client:
            create_object_response = await client.post(
                "/custom-objects",
                json={
                    "object_name_singular": "request",
                    "object_name_plural": "requests",
                    "object_label_singular": "Request",
                    "object_label_plural": "Requests",
                },
            )
            self.assertEqual(create_object_response.status_code, 201)

            create_title_field_response = await client.post(
                "/custom-objects/request/fields",
                json={
                    "field_type": "string",
                    "field_name": "title",
                    "label": "Title",
                    "is_nullable": False,
                },
            )
            self.assertEqual(create_title_field_response.status_code, 201)

            create_relation_field_response = await client.post(
                "/custom-objects/request/fields",
                json={
                    "field_type": "relation",
                    "field_name": "contact_id",
                    "label": "Contact",
                    "relation_target_object_name": "contact",
                    "settings": {"on_delete": "cascade"},
                },
            )
            self.assertEqual(create_relation_field_response.status_code, 201)

        async with self.session_factory() as session:
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__contacts" '
                    '("id", "name_first_name", "name_last_name", "name_middle_name") '
                    "VALUES (:id, :first_name, :last_name, :middle_name)"
                ),
                {
                    "id": str(contact_id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "middle_name": "Michael",
                },
            )
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__requests" '
                    '("id", "title", "contact_id") '
                    "VALUES (:id, :title, :contact_id)"
                ),
                {
                    "id": str(request_record_id),
                    "title": "Need approval",
                    "contact_id": str(contact_id),
                },
            )
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url=f"http://{self.host}",
        ) as client:
            get_record_response = await client.get(
                f"/custom-objects/request/records/{request_record_id}"
            )

        self.assertEqual(get_record_response.status_code, 200)
        payload = get_record_response.json()
        self.assertEqual(payload["id"], str(request_record_id))
        self.assertEqual(payload["title"], "Need approval")
        self.assertEqual(payload["contact_id"], str(contact_id))

    async def test_get_system_object_from_custom_endpoint_returns_404(self) -> None:
        contact_id = uuid4()
        async with self.session_factory() as session:
            await session.execute(
                text(
                    f'INSERT INTO "{self.schema}__contacts" '
                    '("id", "name_first_name", "name_last_name", "name_middle_name") '
                    "VALUES (:id, :first_name, :last_name, :middle_name)"
                ),
                {
                    "id": str(contact_id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "middle_name": "Michael",
                },
            )
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url=f"http://{self.host}",
        ) as client:
            response = await client.get(
                f"/custom-objects/contact/records/{contact_id}"
            )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
