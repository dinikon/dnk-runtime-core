"""Миграция, HTTP round-trip и конкуренция на одноразовом PostgreSQL."""

import asyncio
import os
import unittest
from dataclasses import replace
from uuid import UUID, uuid4
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from src.config import dnk_config
from src.modules.channels.infrastructure.crypto.cipher import ChannelSecretCipher
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.presentation.depends import get_cipher
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.channels_support import channel_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class ChannelsPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant, self.other, self.actor = uuid4(), uuid4(), uuid4()
        naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.schemas = [
            naming.schema_name(EntityIdVO(t)) for t in (self.tenant, self.other)
        ]
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app = channel_app(self.sessions, self.context, scoped_connection=True)
        self.cipher = ChannelSecretCipher(Fernet.generate_key().decode())
        self.app.dependency_overrides[get_cipher] = lambda: self.cipher
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.base = "/api/console/channels"

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def create(self):
        response = await self.client.post(
            self.base,
            headers=self.headers,
            json=dict(
                name="Store",
                kind="woocommerce",
                config_version=1,
                connection_settings=dict(
                    url="https://shop.example/store/",
                    consumer_key="key-original",
                    consumer_secret="secret-original",
                ),
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def rows(self):
        async with self.sessions() as session:
            rows = await session.execute(
                select(ChannelModel.__table__).execution_options(
                    schema_translate_map={"tenant": self.schemas[0]}
                )
            )
            return rows.mappings().all()

    async def test_crud_encryption_and_tenant_isolation(self):
        record = await self.create()
        url = self.base + "/" + record["id"]
        self.assertEqual((await self.client.get(url)).json(), record)
        rows = await self.rows()
        self.assertNotIn("secret-original", repr(rows))
        self.assertEqual(
            self.cipher.decrypt(rows[0]["encrypted_secrets"])["consumer_secret"],
            "secret-original",
        )
        response = await self.client.patch(
            url, headers=self.headers, json={"name": "Renamed", "is_active": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_active"])
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={
                "config_version": 1,
                "connection_settings": {"consumer_secret": "replacement"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        row = (await self.rows())[0]
        self.assertEqual(
            self.cipher.decrypt(row["encrypted_secrets"]),
            {"consumer_key": "key-original", "consumer_secret": "replacement"},
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        other_headers = self.headers | {"X-CSRF-Token": token}
        self.assertEqual((await self.client.get(self.base)).json(), [])
        self.assertEqual((await self.client.get(url)).status_code, 404)
        self.assertEqual(
            (
                await self.client.patch(
                    url, headers=other_headers, json={"name": "Wrong tenant"}
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.delete(url, headers=other_headers)).status_code, 404
        )
        self.app.state.test_context = self.context
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        response = await self.client.delete(
            url, headers=self.headers | {"X-CSRF-Token": token}
        )
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(await self.rows(), [])

    async def test_concurrent_patches_merge_under_row_lock(self):
        record = await self.create()
        url = self.base + "/" + record["id"]
        responses = await asyncio.gather(
            self.client.patch(
                url,
                headers=self.headers,
                json={
                    "config_version": 1,
                    "connection_settings": {"consumer_key": "key-new"},
                },
            ),
            self.client.patch(
                url,
                headers=self.headers,
                json={
                    "config_version": 1,
                    "connection_settings": {"consumer_secret": "secret-new"},
                },
            ),
        )
        self.assertEqual(
            [r.status_code for r in responses], [200, 200], [r.text for r in responses]
        )
        row = (await self.rows())[0]
        self.assertEqual(
            self.cipher.decrypt(row["encrypted_secrets"]),
            {"consumer_key": "key-new", "consumer_secret": "secret-new"},
        )

    async def test_failed_patch_rolls_back_and_reads_work_without_key(self):
        record = await self.create()
        url = self.base + "/" + record["id"]
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={
                "name": "Wrong",
                "config_version": 1,
                "connection_settings": {"consumer_secret": ""},
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual((await self.client.get(url)).json(), record)
        self.app.dependency_overrides[get_cipher] = lambda: ChannelSecretCipher("")
        self.assertEqual((await self.client.get(url)).json(), record)
        response = await self.client.patch(
            url, headers=self.headers, json={"name": "No cipher needed"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={
                "config_version": 1,
                "connection_settings": {"consumer_secret": "new"},
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            (await self.client.get(url)).json()["name"], "No cipher needed"
        )

    async def test_migration_matches_metadata_and_downgrades(self):
        async with self.engine.begin() as connection:
            columns = await connection.run_sync(
                lambda sync: inspect(sync).get_columns(
                    "channels", schema=self.schemas[0]
                )
            )
            self.assertEqual(
                {c["name"] for c in columns}, set(ChannelModel.__table__.c.keys())
            )
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0012_catalog"
            )
            exists = await connection.run_sync(
                lambda sync: inspect(sync).has_table("channels", schema=self.schemas[0])
            )
            self.assertFalse(exists)
            await TenantMigrator().upgrade(connection, self.schemas[0])
