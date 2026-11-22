"""Дерево, назначения и наследование на полном HTTP-пути Catalog."""

import asyncio
import os
import unittest

from sqlalchemy import inspect, text

from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)

from test import test_catalog_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class CatalogCategoriesPostgresTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = support.CatalogPostgresTests.asyncSetUp
    asyncTearDown = support.CatalogPostgresTests.asyncTearDown
    request = support.CatalogPostgresTests.request

    async def category(self, name, parent=None):
        return (
            await self.request(
                "POST",
                "/categories",
                {"locale": "ru", "name": name, "parent_id": parent},
                201,
            )
        )["id"]

    async def test_item_categories_and_lifecycle(self):
        (default,) = (await self.request("GET", "/categories?locale=en"))["items"]
        self.assertEqual(default["name"], "Uncategorized")
        root = await self.category("Одежда")
        tops = await self.category("Топы", root)
        summer = await self.category("Лето")
        await self.request("PATCH", "/categories/" + root, {"parent_id": tops}, 409)
        await self.request("DELETE", "/categories/" + root, status=409)
        await self.request(
            "PATCH", "/categories/" + tops, {"translations": {"en": "Tops"}}
        )
        await self.request("PATCH", "/categories/" + tops, {"parent_id": None})
        tree = {
            node["id"]: node
            for node in (await self.request("GET", "/categories?locale=en"))["items"]
        }
        self.assertEqual(tree[tops]["name"], "Tops")
        self.assertIsNone(tree[tops]["parent_id"])
        self.assertIsNone(tree[summer]["name"])
        self.assertEqual(tree[summer]["fallback_locale"], "ru")
        self.assertEqual(tree[summer]["fallback_name"], "Лето")
        await self.request("PUT", "/categories/default", {"category_id": tops})
        simple = (await self.request("POST", "/items", {}, 201))["id"]
        self.assertEqual(
            (await self.request("GET", f"/items/{simple}?locale=en"))["item"][
                "categories"
            ]["primary_category_id"],
            tops,
        )
        selection = {"primary_category_id": tops, "additional_category_ids": [summer]}
        item = (
            await self.request(
                "POST",
                "/items",
                {"kind": "variable", "variants": [{}], "categories": selection},
                201,
            )
        )["id"]
        child = (await self.request("GET", f"/items/{item}/variants?locale=en"))[
            "items"
        ][0]["id"]
        child_path = f"/items/{item}/variants/{child}"
        await self.request(
            "PATCH", f"/items/{item}", {"categories": {"primary_category_id": summer}}
        )
        promoted = {"primary_category_id": summer, "additional_category_ids": [tops]}
        async with self.engine.connect() as conn:
            assignments = await conn.execute(
                text(
                    f"SELECT catalog_item_id::text, category_id::text, is_default "
                    f'FROM "{self.schemas[0]}".catalog_item_categories '
                    "WHERE catalog_item_id IN (:parent, :variant)"
                ),
                {"parent": item, "variant": child},
            )
            self.assertCountEqual(
                assignments.all(), [(item, summer, True), (item, tops, False)]
            )
        self.assertEqual(
            (await self.request("GET", child_path + "?locale=en"))["item"][
                "categories"
            ],
            promoted,
        )
        await self.request("PATCH", child_path, {"categories": selection}, 422)
        await self.request(
            "PATCH",
            f"/items/{item}",
            {
                "categories": {
                    "primary_category_id": tops,
                    "additional_category_ids": [tops],
                }
            },
            422,
        )
        await self.request("DELETE", "/categories/" + summer, status=409)
        await self.request("DELETE", "/categories/" + tops, status=409)
        await self.request("DELETE", "/categories/" + root, status=204)

    async def test_concurrent_moves_cannot_create_a_cycle(self):
        left, right = await self.category("A"), await self.category("B")

        async def move(node, parent):
            return await self.client.patch(
                self.base + "/categories/" + node,
                json={"parent_id": parent},
                headers=self.headers,
            )

        responses = await asyncio.gather(move(left, right), move(right, left))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])

    async def test_concurrent_default_changes_leave_one_flag(self) -> None:
        """Смена настройки каталога сохраняет уже назначенную товару категорию."""
        before = (await self.request("POST", "/items", {}, 201))["id"]
        (initial,) = (await self.request("GET", "/categories?locale=ru"))["items"]
        choices = [await self.category("Одежда"), await self.category("Обувь")]
        responses = await asyncio.gather(
            *(
                self.client.put(
                    self.base + "/categories/default",
                    json={"category_id": choice},
                    headers=self.headers,
                )
                for choice in choices
            )
        )
        self.assertEqual([response.status_code for response in responses], [200, 200])
        nodes = (await self.request("GET", "/categories?locale=ru"))["items"]
        (selected,) = [node["id"] for node in nodes if node["is_default"]]
        self.assertIn(selected, choices)
        after = (await self.request("POST", "/items", {}, 201))["id"]
        for item, expected in ((before, initial["id"]), (after, selected)):
            card = (await self.request("GET", f"/items/{item}?locale=ru"))["item"]
            self.assertEqual(card["categories"]["primary_category_id"], expected)

    async def test_backfill_and_tenant_isolation(self):
        """Проверяет upgrade существующего каталога и изоляцию его справочника."""
        simple = (await self.request("POST", "/items", {"sku": "existing"}, 201))["id"]
        root = (
            await self.request(
                "POST", "/items", {"kind": "variable", "variants": [{}]}, 201
            )
        )["id"]
        migrator = TenantMigrator()
        async with self.engine.begin() as conn:
            await migrator.downgrade(
                conn, self.schemas[0], "0022_catalog_purchase_price"
            )
            await migrator.upgrade(conn, self.schemas[0])
            foreign = await conn.scalar(
                text(
                    f'SELECT id FROM "{self.schemas[1]}".catalog_categories WHERE is_default'
                )
            )
        (default,) = (await self.request("GET", "/categories?locale=ru"))["items"]
        for identifier in [simple, root]:
            item = (await self.request("GET", f"/items/{identifier}?locale=ru"))["item"]
            self.assertEqual(
                item["categories"],
                {"primary_category_id": default["id"], "additional_category_ids": []},
            )
        self.assertNotEqual(str(foreign), default["id"])
        await self.request(
            "PATCH",
            f"/items/{simple}",
            {"sku": "unexpected", "categories": {"primary_category_id": str(foreign)}},
            422,
        )
        self.assertEqual(
            (await self.request("GET", f"/items/{simple}?locale=ru"))["item"]["sku"],
            "existing",
        )

    async def test_dropping_source_locale_preserves_names_and_membership(self) -> None:
        """Проверяет старые данные при смене ревизии и выбор резервного названия."""
        parent = await self.category("Одежда")
        category = await self.category("Топы", parent)
        await self.request(
            "PATCH", f"/categories/{category}", {"translations": {"en": "Tops"}}
        )
        selection = {"primary_category_id": category, "additional_category_ids": []}
        item = (await self.request("POST", "/items", {"categories": selection}, 201))[
            "id"
        ]
        schema = self.schemas[0]
        migrator = TenantMigrator()
        async with self.engine.begin() as conn:
            await migrator.downgrade(conn, schema, "0024_fb_publication_timestamps")
            await conn.execute(
                text(
                    f'UPDATE "{schema}".catalog_categories '
                    "SET source_locale = 'ru' WHERE id = :id"
                ),
                {"id": category},
            )
            await migrator.upgrade(conn, schema)
            columns = await conn.run_sync(
                lambda connection: inspect(connection).get_columns(
                    "catalog_categories", schema=schema
                )
            )
            self.assertNotIn("source_locale", {column["name"] for column in columns})

        for locale, expected in (("ru", "Топы"), ("en", "Tops"), ("fr", None)):
            rows = (await self.request("GET", f"/categories?locale={locale}"))["items"]
            row = next(value for value in rows if value["id"] == category)
            self.assertEqual(row["name"], expected)
            self.assertEqual(row["parent_id"], parent)
            self.assertEqual(row["fallback_locale"], "en")
            self.assertEqual(row["fallback_name"], "Tops")
        card = (await self.request("GET", f"/items/{item}?locale=ru"))["item"]
        self.assertEqual(card["categories"], selection)
