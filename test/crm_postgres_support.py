"""Общая PostgreSQL-сборка CRM для межмодульных HTTP-проверок."""

import os
import unittest
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.crm.presentation.contact.router import router as contact_router
from src.modules.crm.presentation.counterparty_reference.router import (
    router as counterparty_router,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.crm_company_support import company_app


class CrmPostgresTestCase(unittest.IsolatedAsyncioTestCase):
    """Предоставляет две tenant-схемы, HTTP-клиент и компанию без внешних источников."""

    async def asyncSetUp(self) -> None:
        """Мигрирует изолированные схемы и создаёт компанию через HTTP."""
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], poolclass=NullPool
        )
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schemas = [
            self.naming.schema_name(value) for value in (self.tenant, self.other)
        ]
        self.addAsyncCleanup(self.drop_schemas)
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(uuid4()), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app = company_app(self.sessions, self.context, scoped_connection=True)
        self.app.include_router(counterparty_router, prefix="/api/console")
        self.app.include_router(contact_router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        response = await self.client.post(
            "/api/console/crm/companies",
            headers=self.headers,
            json={"legal_name": "Supplier ACME"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.company = response.json()

    async def drop_schemas(self) -> None:
        """Удаляет только временные tenant-схемы текущего теста."""
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
