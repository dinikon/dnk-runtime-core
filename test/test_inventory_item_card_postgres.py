"""Полная карточка SKU: атомарное изменение идентичности и дочернего состава через HTTP."""

import os
import unittest

from uuid import uuid4
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.inventory.presentation.packaging_type.router import (
    router as packaging_type_router,
)
from test.inventory_item_support import inventory_item_app


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class InventoryItemCardPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет совместные PATCH/DELETE и сохранность независимых справочников."""

    async def asyncSetUp(self) -> None:
        """Создаёт товар с двумя штрихкодами, упаковками и самостоятельным типом тары."""
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], poolclass=NullPool
        )
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        tenant = EntityIdVO(uuid4())
        self.schema = self.naming.schema_name(tenant)
        self.addAsyncCleanup(self.drop_schema)
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(self.schema))
            await TenantMigrator().upgrade(connection, self.schema)
        context = RequestContext(
            Principal(str(uuid4()), str(tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        app = inventory_item_app(self.sessions, context, scoped_connection=True)
        app.include_router(packaging_type_router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "item", "barcodes": ["0001", "0002"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.item = response.json()
        self.item_url = f"/api/console/inventory/items/{self.item['id']}"
        self.url = f"{self.item_url}/packagings"
        response = await self.client.post(
            "/api/console/inventory/packaging-types",
            headers=self.headers,
            json={"code": "BOX", "name": "Ящик"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.kind = response.json()
        self.packagings = []
        for code in ("BOX", "CAN"):
            response = await self.create(code)
            self.assertEqual(response.status_code, 201, response.text)
            self.packagings.append(response.json())

    async def drop_schema(self) -> None:
        """Удаляет только собственную временную tenant-схему после HTTP-проверки."""
        async with self.engine.begin() as connection:
            await connection.execute(
                DropSchema(self.schema, cascade=True, if_exists=True)
            )

    async def create(self, code: str) -> Response:
        """Создаёт дочернюю упаковку через настоящий HTTP и общий UoW."""
        return await self.client.post(
            self.url,
            headers=self.headers,
            json={
                "packaging_type_id": self.kind["id"],
                "code": code,
                "name": "Ящик",
                "content_quantity": "12",
                "content_uom": "PCS",
            },
        )

    async def test_identity_patch_preserves_unchanged_barcode_ids_and_packagings(
        self,
    ) -> None:
        """Сохраняет ID после trim/перестановки, выдаёт ID новому коду и не теряет упаковки."""
        response = await self.client.patch(
            self.item_url,
            headers=self.headers,
            json={"sku": " Straße-01 ", "barcodes": [" 0002 ", "000New", "0001"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        card = response.json()
        self.assertEqual(card["sku"], "strasse-01")
        self.assertEqual(
            [row["barcode"] for row in card["barcodes"]], ["0002", "000New", "0001"]
        )
        self.assertEqual(card["barcodes"][0]["id"], self.item["barcodes"][1]["id"])
        self.assertEqual(card["barcodes"][2]["id"], self.item["barcodes"][0]["id"])
        self.assertNotIn(
            card["barcodes"][1]["id"], [row["id"] for row in self.item["barcodes"]]
        )
        self.assertEqual((await self.client.get(self.item_url)).json(), card)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"], self.packagings
        )
        cleared = await self.client.patch(
            self.item_url, headers=self.headers, json={"barcodes": []}
        )
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(cleared.json()["barcodes"], [])
        self.assertEqual(cleared.json()["sku"], "strasse-01")
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"], self.packagings
        )

    async def test_identity_conflicts_roll_back_the_entire_card(self) -> None:
        """UNIQUE-конфликт SKU либо штрихкода откатывает все поля и оба дочерних состава."""
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "occupied", "barcodes": ["TAKEN"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        for payload in (
            {"sku": "OCCUPIED", "barcodes": ["new"]},
            {"sku": "otherwise-free", "barcodes": ["0002", "TAKEN"]},
        ):
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    self.item_url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(
                    (await self.client.get(self.item_url)).json(), self.item
                )
                self.assertEqual(
                    (await self.client.get(self.url)).json()["items"], self.packagings
                )

    async def test_delete_card_cascades_both_owned_collections_only(self) -> None:
        """Пустой 204 удаляет детей, сохраняя тип тары и независимую позицию."""
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "other", "barcodes": ["other-barcode"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        other = response.json()
        response = await self.client.delete(self.item_url, headers=self.headers)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.assertNotIn("content-type", response.headers)
        self.assertEqual((await self.client.get(self.item_url)).status_code, 404)
        for packaging in self.packagings:
            self.assertEqual(
                (await self.client.get(f"{self.url}/{packaging['id']}")).status_code,
                404,
            )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/packaging-types/{self.kind['id']}"
                )
            ).json(),
            self.kind,
        )
        self.assertEqual(
            (
                await self.client.get(f"/api/console/inventory/items/{other['id']}")
            ).json(),
            other,
        )
