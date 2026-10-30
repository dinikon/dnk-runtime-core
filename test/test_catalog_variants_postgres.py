"""Вложенные позиции: HTTP, реальные FK, наследование и публичный снимок."""

import unittest
from uuid import UUID, uuid4
from sqlalchemy import text
from test.test_catalog_postgres import CatalogPostgresTests
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.query import (
    GetCatalogProductSnapshotQuery,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogVariantsPostgresTests(CatalogPostgresTests):
    async def test_list_stock_projection(self) -> None:
        """Списки передают количество и источник без копирования общего запаса детям."""
        root = (
            await self.request(
                "POST",
                "/items",
                {
                    "kind": "variable",
                    "stock": {
                        "manage_stock": True,
                        "stock_quantity": 7,
                        "stock_status": None,
                        "backorders": "notify",
                    },
                },
                201,
            )
        )["id"]
        inherited = (await self.request("POST", f"/items/{root}/variants", {}, 201))[
            "id"
        ]
        own = (
            await self.request(
                "POST",
                f"/items/{root}/variants",
                {
                    "stock": {
                        "manage_stock": True,
                        "stock_quantity": 0,
                        "stock_status": None,
                        "backorders": "no",
                    },
                },
                201,
            )
        )["id"]
        rows = (await self.request("GET", f"/items/{root}/variants?locale=en"))["items"]
        by_id = {row["id"]: row for row in rows}
        self.assertTrue(by_id[inherited]["manage_stock"])
        self.assertEqual(by_id[inherited]["stock_quantity"], 7)
        self.assertEqual(by_id[inherited]["stock_source"], "parent")
        self.assertEqual(by_id[own]["stock_quantity"], 0)
        self.assertEqual(by_id[own]["stock_source"], "own")
        roots = (await self.request("GET", "/items?locale=en"))["items"]
        self.assertEqual(roots[0]["stock_quantity"], 7)
        self.assertEqual(roots[0]["stock_source"], "own")
        await self.request(
            "PATCH",
            f"/items/{root}",
            {
                "stock": {
                    "manage_stock": False,
                    "stock_quantity": None,
                    "stock_status": "in_stock",
                    "backorders": "no",
                },
            },
        )
        rows = (await self.request("GET", f"/items/{root}/variants?locale=en"))["items"]
        manual = next(row for row in rows if row["id"] == inherited)
        self.assertFalse(manual["manage_stock"])
        self.assertIsNone(manual["stock_quantity"])
        self.assertEqual(manual["stock_source"], "own")

    async def test_variant_flow_and_atomic_failures(self) -> None:
        root = (
            await self.request(
                "POST",
                "/items",
                {
                    "kind": "variable",
                    "sku": "FAMILY",
                    "translations": {
                        "en": {
                            "expected_schema_version": 1,
                            "values": {"title": "Parent", "body": "Description"},
                        }
                    },
                    "stock": {
                        "manage_stock": True,
                        "stock_quantity": 7,
                        "stock_status": None,
                        "backorders": "no",
                    },
                },
                201,
            )
        )["id"]
        child = (
            await self.request(
                "POST",
                f"/items/{root}/variants",
                {
                    "sku": "CHILD",
                    "status": "active",
                    "price_specification": {
                        "regular_price": "12.345678",
                        "currency": "UAH",
                    },
                },
                201,
            )
        )["id"]
        path = f"/items/{root}/variants/{child}"
        value = (await self.request("GET", path + "?locale=en"))["item"]
        self.assertIsNone(value["content"])
        self.assertFalse(value["stock"]["manage_stock"])
        self.assertEqual(value["stock"]["stock_status"], "in_stock")
        self.assertEqual(value["effective_content"]["title"], "Parent")
        self.assertEqual(value["effective_stock"]["stock_quantity"], 7)
        self.assertEqual(value["sources"]["stock"], root)
        self.assertFalse(value["available_for_sale"])
        await self.request("PATCH", f"/items/{root}", {"status": "active"})
        value = (await self.request("GET", path + "?locale=en"))["item"]
        self.assertTrue(value["available_for_sale"])
        self.assertEqual(value["price"], "12.345678")
        await self.request(
            "PATCH",
            path + "?locale=en",
            {
                "content": {"expected_schema_version": 1, "values": {"body": ""}},
                "gallery": {"images": [], "primary_image_id": None},
            },
        )
        value = (await self.request("GET", path + "?locale=en"))["item"]
        self.assertEqual(value["effective_content"], {"title": "Parent", "body": ""})
        self.assertEqual(value["sources"]["body"], child)
        self.assertEqual(value["effective_gallery"]["images"], [])
        await self.request("PATCH", f"/items/{root}?locale=en", {"content": None}, 422)
        self.assertEqual(
            (await self.request("GET", path + "?locale=en"))["item"][
                "effective_content"
            ]["title"],
            "Parent",
        )
        await self.request(
            "PATCH", path, {"sku": "MUST-NOT-SAVE", "status": "archived"}, 422
        )
        self.assertEqual(
            (await self.request("GET", path + "?locale=en"))["item"]["sku"], "CHILD"
        )
        await self.request("DELETE", path, status=422)
        await self.request("PATCH", path, {"stock_source": "own"}, 422)
        await self.request(
            "PATCH",
            path,
            {
                "stock": {
                    "manage_stock": False,
                    "stock_quantity": None,
                    "stock_status": "out_of_stock",
                    "backorders": "no",
                },
            },
        )
        await self.request("PATCH", path, {"stock_source": "parent"}, 422)
        await self.request("PATCH", path, {"stock": None}, 422)
        await self.request(
            "PATCH", path + "?locale=en", {"content": None, "gallery": None}
        )
        value = (await self.request("GET", path + "?locale=en"))["item"]
        self.assertEqual(value["effective_content"]["body"], "Description")
        await self.request("PATCH", f"/items/{root}", {"sku": "CHILD"}, 409)
        await self.request(
            "PATCH",
            f"/items/{root}",
            {"price_specification": {"regular_price": "5", "currency": "UAH"}},
            422,
        )
        result = await self.request("GET", "/items?locale=en&search=CHILD")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], root)
        self.assertEqual(result["items"][0]["variant_count"], 1)
        await self.request(
            "GET", f"/items/{uuid4()}/variants/{child}?locale=en", status=404
        )
        await self.request("PATCH", f"/items/{root}", {"status": "draft"})
        await self.request("DELETE", path, status=204)
        await self.request("PATCH", f"/items/{root}", {"status": "active"}, 422)
        await self.request("DELETE", f"/items/{root}", status=204)

    async def test_atomic_creation_and_parent_delete(self) -> None:
        await self.request(
            "POST", "/items", {"kind": "variable", "status": "active"}, 422
        )
        self.assertEqual((await self.request("GET", "/items?locale=en"))["total"], 0)
        root = (
            await self.request(
                "POST",
                "/items",
                {
                    "kind": "variable",
                    "status": "active",
                    "variants": [{"sku": "FIRST"}, {"sku": "SECOND"}],
                },
                201,
            )
        )["id"]
        children = await self.request(
            "GET", f"/items/{root}/variants?locale=en&limit=1&offset=1"
        )
        self.assertEqual(children["total"], 2)
        self.assertEqual(len(children["items"]), 1)
        await self.request("PATCH", f"/items/{root}", {"kind": "simple"}, 422)
        await self.request("DELETE", f"/items/{root}", status=204)
        async with self.engine.connect() as connection:
            count = await connection.scalar(
                text(f'SELECT count(*) FROM "{self.schemas[0]}".catalog_item')
            )
            self.assertEqual(count, 0)

    async def test_migration_refuses_lossy_downgrade(self) -> None:
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
            TenantMigrator,
        )

        await self.request(
            "POST", "/items", {"kind": "variable", "sku": "CONTAINER"}, 201
        )
        with self.assertRaisesRegex(RuntimeError, "SKU"):
            async with self.engine.begin() as connection:
                await TenantMigrator().downgrade(
                    connection, self.schemas[0], "0007_channels_publications"
                )
        self.assertEqual((await self.request("GET", "/items?locale=en"))["total"], 1)

    async def test_public_snapshot_import_collision_and_tenant_isolation(self) -> None:
        from dataclasses import replace
        from src.modules.catalog.domain.catalog_item.value_object.identifier import (
            CatalogItemIdVO,
        )
        from src.modules.catalog.domain.error import CatalogConflictError
        from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
            SqlAlchemyCatalogItemQueryRepository,
        )
        from src.modules.catalog.infrastructure.mutation_lock import (
            PostgresCatalogMutationLock,
        )
        from src.modules.catalog.infrastructure.catalog_import.repository import (
            SqlAlchemyImportRows,
        )
        from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.handler import (
            GetCatalogProductSnapshotHandler,
        )
        from src.modules.shared.infrastructure.time.utc_clock import UtcClock
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )

        root = (
            await self.request(
                "POST",
                "/items",
                {
                    "kind": "variable",
                    "sku": "PARENT",
                    "translations": {
                        "en": {
                            "expected_schema_version": 1,
                            "values": {"title": "Parent"},
                        }
                    },
                    "variants": [{"sku": "CHILD"}],
                },
                201,
            )
        )["id"]
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant.uuid, self.naming
            )
            handler = GetCatalogProductSnapshotHandler(
                SqlAlchemyCatalogItemQueryRepository(session),
                UtcClock(),
                PostgresCatalogMutationLock(session),
            )
            result = await handler.execute(
                GetCatalogProductSnapshotQuery(
                    self.tenant, CatalogItemIdVO(UUID(root)), "en"
                )
            )
            self.assertEqual(result.root.kind, "variable")
            self.assertEqual(len(result.variants), 1)
            variant = result.variants[0]
            self.assertIsNone(variant.content)
            self.assertEqual(variant.effective_content["title"], "Parent")
            self.assertEqual(variant.sources.title, UUID(root))
            rows = SqlAlchemyImportRows(session)
            for sku in ("PARENT", "CHILD"):
                with self.assertRaises(CatalogConflictError):
                    await rows.find_item(sku)
            await session.rollback()
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            await self.request("GET", f"/items/{root}/variants?locale=en", status=404)
            await self.request("POST", f"/items/{root}/variants", {}, 404)
        finally:
            self.app.state.test_context = original

    async def test_gallery_inheritance_and_own_upload_streams(self) -> None:
        import base64
        from unittest.mock import AsyncMock
        from src.modules.catalog.presentation.catalog_item.depends import get_files
        from src.modules.catalog.application.catalog_item.port.files import (
            UploadedCatalogImageFile,
            CatalogImageFileContent,
        )

        data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4X8AAAAASUVORK5CYII="
        )

        class Stream:
            closed = False

            def __aiter__(self):
                async def chunks():
                    yield data

                return chunks()

            async def aclose(self):
                self.closed = True

        streams = []

        async def content(tenant, file_id):
            self.assertEqual(tenant, self.tenant.uuid)
            stream = Stream()
            streams.append(stream)
            return CatalogImageFileContent(
                file_id, "image.png", "image/png", len(data), stream
            )

        files = AsyncMock()
        files.upload.side_effect = lambda *args: UploadedCatalogImageFile(
            uuid4(), "image.png", "image/png", len(data)
        )
        files.content.side_effect = content
        self.app.dependency_overrides[get_files] = lambda: files
        root = (
            await self.request(
                "POST", "/items", {"kind": "variable", "variants": [{}]}, 201
            )
        )["id"]
        child = (await self.request("GET", f"/items/{root}/variants?locale=en"))[
            "items"
        ][0]["id"]

        async def upload(path):
            response = await self.client.post(
                self.base + path,
                headers=self.headers,
                files={"image": ("image.png", data, "image/png")},
            )
            self.assertEqual(response.status_code, 201, response.text)
            return response.json()["image_id"]

        parent_image = await upload(f"/items/{root}/images/en/upload")
        path = f"/items/{root}/variants/{child}"
        read = (await self.request("GET", path + "?locale=en"))["item"]
        self.assertIsNone(read["gallery"])
        self.assertEqual(read["effective_gallery"]["images"][0]["id"], parent_image)
        response = await self.client.get(
            self.base + path + f"/images/en/{parent_image}/content"
        )
        self.assertEqual(response.content, data)
        self.assertTrue(streams[-1].closed)
        own_image = await upload(path + "/images/en/upload")
        read = (await self.request("GET", path + "?locale=en"))["item"]
        self.assertEqual([v["id"] for v in read["gallery"]["images"]], [own_image])
        await self.request(
            "GET", path + f"/images/en/{parent_image}/content", status=404
        )
        await self.request("PATCH", path + "?locale=en", {"gallery": None})
        response = await self.client.get(
            self.base + path + f"/images/en/{parent_image}/content"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(streams[-1].closed)

    async def test_concurrent_archiving_uses_one_family_lock(self) -> None:
        import asyncio

        root = (
            await self.request(
                "POST",
                "/items",
                {"kind": "variable", "status": "active", "variants": [{}, {}]},
                201,
            )
        )["id"]
        children = (await self.request("GET", f"/items/{root}/variants?locale=en"))[
            "items"
        ]
        results = await asyncio.gather(
            *(
                self.client.patch(
                    self.base + f"/items/{root}/variants/{child['id']}",
                    headers=self.headers,
                    json={"status": "archived"},
                )
                for child in children
            )
        )
        self.assertEqual(sorted(v.status_code for v in results), [200, 422])
        children = (await self.request("GET", f"/items/{root}/variants?locale=en"))[
            "items"
        ]
        self.assertEqual(sum(v["status"] != "archived" for v in children), 1)

    async def test_parent_stock_switch_keeps_manual_statuses_and_own_quantity(
        self,
    ) -> None:
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
            TenantMigrator,
        )

        root = (
            await self.request(
                "POST",
                "/items",
                {
                    "kind": "variable",
                    "variants": [
                        {
                            "stock": {
                                "manage_stock": False,
                                "stock_quantity": None,
                                "stock_status": status,
                                "backorders": "no",
                            }
                        }
                        for status in ("out_of_stock", "on_backorder")
                    ],
                },
                201,
            )
        )["id"]
        children = (await self.request("GET", f"/items/{root}/variants?locale=en"))[
            "items"
        ]
        ids = [v["id"] for v in children]

        async def read(identifier):
            return (
                await self.request(
                    "GET", f"/items/{root}/variants/{identifier}?locale=en"
                )
            )["item"]

        original = [(await read(i))["stock"] for i in ids]
        await self.request(
            "PATCH",
            f"/items/{root}",
            {
                "stock": {
                    "manage_stock": True,
                    "stock_quantity": 13,
                    "stock_status": None,
                    "backorders": "notify",
                }
            },
        )
        for i, own in zip(ids, original):
            item = await read(i)
            self.assertEqual(item["stock"], own)
            self.assertEqual(item["effective_stock"]["stock_quantity"], 13)
            self.assertEqual(item["sources"]["stock"], root)
        await self.request(
            "PATCH",
            f"/items/{root}/variants/{ids[0]}",
            {
                "stock": {
                    "manage_stock": True,
                    "stock_quantity": -1,
                    "stock_status": None,
                    "backorders": "yes",
                }
            },
        )
        own = await read(ids[0])
        self.assertEqual(own["effective_stock"]["stock_quantity"], -1)
        self.assertEqual(own["stock_source"], "own")
        await self.request(
            "PATCH",
            f"/items/{root}",
            {
                "stock": {
                    "manage_stock": False,
                    "stock_quantity": None,
                    "stock_status": "in_stock",
                    "backorders": "no",
                }
            },
        )
        self.assertEqual((await read(ids[1]))["stock_status"], "on_backorder")
        self.assertEqual((await read(ids[0]))["effective_stock"]["stock_quantity"], -1)
        # SKU-null families and child own settings survive downgrade/upgrade.
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0007_channels_publications"
            )
            columns = (
                await connection.execute(
                    text(
                        "SELECT column_name,is_nullable FROM information_schema.columns WHERE table_schema=:schema AND table_name='catalog_item'"
                    ),
                    {"schema": self.schemas[0]},
                )
            ).all()
            self.assertNotIn("stock_source", dict(columns))
            self.assertEqual(dict(columns)["manage_stock"], "NO")
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual((await read(ids[1]))["stock"], original[1])


def load_tests(loader, tests, pattern):
    """Не повторяет базовый набор; он запускается отдельным модулем."""
    return unittest.TestSuite(
        CatalogVariantsPostgresTests(name)
        for name in CatalogVariantsPostgresTests.__dict__
        if name.startswith("test_")
    )
