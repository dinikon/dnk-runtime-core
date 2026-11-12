"""Атомарная связь SKU, tenant-изоляция, миграция и удаление на PostgreSQL."""

import asyncio
import os
import unittest
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import test.test_catalog_postgres as support
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku
from src.modules.inventory.presentation.inventory_item.router import (
    router as inventory_router,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"),
    "TEST_POSTGRES_URL requires a disposable database",
)
class CatalogInventoryPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Использует настоящий HTTP, общий UoW и независимые tenant-схемы."""

    asyncSetUpBase = support.CatalogPostgresTests.asyncSetUp
    asyncTearDown = support.CatalogPostgresTests.asyncTearDown
    request = support.CatalogPostgresTests.request

    async def asyncSetUp(self) -> None:
        """Подключает оба модуля к одной проверяемой HTTP-сборке."""
        await self.asyncSetUpBase()
        self.app.include_router(inventory_router, prefix="/api/console")
        self.inventory_url = "/api/console/inventory/items"

    async def create_item(self, inventory_item: dict[str, str] | None = None) -> str:
        """Создаёт CatalogItem с необязательным явным выбором SKU."""
        result = await self.request(
            "POST", "/items", {"inventory_item": inventory_item}, 201
        )
        return result["id"]

    async def rows(self, table: str) -> list[dict[str, object]]:
        """Читает только тестовую схему для проверки фактически сохранённых данных."""
        self.assertIn(
            table, {"catalog_item", "inventory_items", "inventory_item_barcodes"}
        )
        async with self.engine.connect() as connection:
            result = await connection.execute(
                text(f'SELECT * FROM "{self.schemas[0]}".{table}')
            )
            return [dict(row) for row in result.mappings()]

    async def test_default_creation_reuse_rename_and_search(self) -> None:
        """Defaults создаются один раз, переименование сохраняет FK и обновляет read-проекции."""
        item = await self.create_item()
        first = await self.request(
            "PUT", f"/items/{item}/sku", {"mode": "create", "sku": " Straße-01 "}
        )
        self.assertTrue(first["inventory_item_created"])
        self.assertEqual(first["sku"], "strasse-01")
        stored = (await self.rows("inventory_items"))[0]
        self.assertEqual(
            (
                stored["base_uom"],
                stored["quantity_step"],
                stored["tracking_mode"],
                stored["expiration_mode"],
            ),
            ("PCS", Decimal("1"), "NONE", "NONE"),
        )
        self.assertEqual(await self.rows("inventory_item_barcodes"), [])
        repeated = await self.request(
            "PUT", f"/items/{item}/sku", {"mode": "create", "sku": "STRASSE-01"}
        )
        self.assertFalse(repeated["inventory_item_created"])
        self.assertEqual(repeated["inventory_item_id"], first["inventory_item_id"])
        renamed = await self.client.patch(
            f"{self.inventory_url}/{first['inventory_item_id']}",
            headers=self.headers,
            json={"sku": "NEW-CODE"},
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)
        detail = (await self.request("GET", f"/items/{item}?locale=en"))["item"]
        self.assertEqual(
            (detail["inventory_item_id"], detail["sku"]),
            (first["inventory_item_id"], "new-code"),
        )
        result = await self.request("GET", "/items?locale=en&search=NEW-CODE")
        self.assertEqual((result["total"], result["items"][0]["sku"]), (1, "new-code"))

    async def test_existing_settings_busy_link_and_tenant_isolation(self) -> None:
        """Выбор сохраняет настройки, чужая и занятая ссылки отклоняются."""
        response = await self.client.post(
            self.inventory_url,
            headers=self.headers,
            json={
                "sku": "Existing",
                "base_uom": "KG",
                "quantity_rules": {"step": "0.001"},
                "tracking_mode": "LOT",
                "expiration_mode": "REQUIRED",
                "barcodes": ["0001"],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        inventory_id = response.json()["id"]
        item = await self.create_item(
            {"mode": "existing", "inventory_item_id": inventory_id}
        )
        before = await self.rows("inventory_items")
        result = await self.request(
            "PUT",
            f"/items/{item}/sku",
            {"mode": "existing", "inventory_item_id": inventory_id},
        )
        self.assertFalse(result["inventory_item_created"])
        self.assertEqual(await self.rows("inventory_items"), before)
        other_item = await self.create_item()
        await self.request(
            "PUT",
            f"/items/{other_item}/sku",
            {"mode": "existing", "inventory_item_id": inventory_id},
            409,
        )
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            await self.request(
                "POST",
                "/items",
                {
                    "inventory_item": {
                        "mode": "existing",
                        "inventory_item_id": inventory_id,
                    }
                },
                404,
            )
            other = await self.create_item({"mode": "create", "sku": "EXISTING"})
            read = (await self.request("GET", f"/items/{other}?locale=en"))["item"]
            self.assertNotEqual(read["inventory_item_id"], inventory_id)
        finally:
            self.app.state.test_context = original

    async def test_linked_settings_patch_preserves_identity_barcodes_and_catalog(
        self,
    ) -> None:
        """Редактирует четыре настройки связанного SKU, сохраняя FK и дочерние ID."""
        created = await self.client.post(
            self.inventory_url,
            headers=self.headers,
            json={
                "sku": "settings",
                "base_uom": "PCS",
                "quantity_rules": {"step": "1"},
                "barcodes": ["000settings"],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        original = created.json()
        item = await self.create_item(
            {"mode": "existing", "inventory_item_id": original["id"]}
        )
        url = f"{self.inventory_url}/{original['id']}"
        step = "0.123456789012345678901234567890123456789"
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={
                "base_uom": "KG",
                "quantity_rules": {"step": step},
                "tracking_mode": "LOT",
                "expiration_mode": "REQUIRED",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        detail = (await self.client.get(url)).json()
        self.assertEqual(detail, response.json())
        self.assertEqual(detail["quantity_rules"], {"step": step})
        for field in ("id", "sku", "barcodes"):
            self.assertEqual(detail[field], original[field])
        catalog = (await self.request("GET", f"/items/{item}?locale=en"))["item"]
        self.assertEqual(catalog["inventory_item_id"], original["id"])
        self.assertEqual(catalog["sku"], original["sku"])
        invalid = await self.client.patch(
            url, headers=self.headers, json={"tracking_mode": "SERIAL"}
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertEqual((await self.client.get(url)).json(), detail)

    async def test_business_delete_guard_all_statuses_and_database_fallback(
        self,
    ) -> None:
        """Любая связь запрещает DELETE в бизнес-логике, прямой SQL защищён FK."""
        item = await self.create_item({"mode": "create", "sku": "linked"})
        inventory_id = (await self.rows("inventory_items"))[0]["id"]
        url = f"{self.inventory_url}/{inventory_id}"
        for status in ("draft", "active", "archived"):
            await self.request("PATCH", f"/items/{item}", {"status": status})
            response = await self.client.delete(url, headers=self.headers)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertIn("связана с элементом каталога", response.json()["detail"])
        with self.assertRaises(IntegrityError) as caught:
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(
                        f'DELETE FROM "{self.schemas[0]}".inventory_items WHERE id=:id'
                    ),
                    {"id": inventory_id},
                )
        self.assertIn("fk_catalog_item_inventory_item", str(caught.exception))
        cleared = await self.request("PUT", f"/items/{item}/sku", {"mode": "clear"})
        self.assertIsNone(cleared["inventory_item_id"])
        self.assertEqual(len(await self.rows("inventory_items")), 1)
        response = await self.client.delete(url, headers=self.headers)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(len(await self.rows("catalog_item")), 1)

    async def test_failed_create_rolls_back_inventory_and_rejects_legacy_write(
        self,
    ) -> None:
        """Ошибка карточки откатывает новый SKU; старые текстовые входы больше не принимаются."""
        await self.request("POST", "/items", {"sku": "legacy"}, 422)
        await self.request(
            "POST",
            "/items",
            {
                "inventory_item": {"mode": "create", "sku": "rollback"},
                "translations": {
                    "en": {
                        "expected_schema_version": 999,
                        "values": {"title": "Broken"},
                    }
                },
            },
            409,
        )
        self.assertEqual(await self.rows("inventory_items"), [])
        self.assertEqual(await self.rows("catalog_item"), [])
        item = await self.create_item()
        await self.request("PATCH", f"/items/{item}", {"sku": "legacy"}, 422)
        for code in ("", "x" * 26, "\u200bsku"):
            await self.request(
                "PUT", f"/items/{item}/sku", {"mode": "create", "sku": code}, 422
            )
        self.assertEqual(await self.rows("inventory_items"), [])

    async def test_parallel_creates_have_one_inventory_and_one_catalog_owner(
        self,
    ) -> None:
        """UNIQUE и общая транзакция закрывают гонку двух созданий одного SKU."""
        body = {"inventory_item": {"mode": "create", "sku": " SHARED "}}
        responses = await asyncio.gather(
            *(
                self.client.post(self.base + "/items", headers=self.headers, json=body)
                for _ in range(2)
            )
        )
        self.assertEqual(
            sorted(response.status_code for response in responses),
            [201, 409],
            [response.text for response in responses],
        )
        self.assertEqual(len(await self.rows("inventory_items")), 1)
        self.assertEqual(len(await self.rows("catalog_item")), 1)

    async def test_variant_owns_reference_and_container_rejects_it(self) -> None:
        """Вариант получает собственный SKU и блокирует удаление независимо от контейнера."""
        root = (await self.request("POST", "/items", {"kind": "variable"}, 201))["id"]
        child = (await self.request("POST", f"/items/{root}/variants", {}, 201))["id"]
        await self.request(
            "PUT", f"/items/{root}/sku", {"mode": "create", "sku": "container"}, 422
        )
        result = await self.request(
            "PUT",
            f"/items/{root}/variants/{child}/sku",
            {"mode": "create", "sku": "CHILD"},
        )
        detail = (
            await self.request("GET", f"/items/{root}/variants/{child}?locale=en")
        )["item"]
        self.assertEqual(
            (detail["sku"], detail["inventory_item_id"]),
            ("child", result["inventory_item_id"]),
        )
        response = await self.client.delete(
            f"{self.inventory_url}/{result['inventory_item_id']}", headers=self.headers
        )
        self.assertEqual(response.status_code, 409, response.text)

    async def test_migration_clears_legacy_codes_without_creating_inventory(
        self,
    ) -> None:
        """Очистка переносит только структуру и не создаёт позиции из старого текста."""
        item = await self.create_item()
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0017_inventory_items"
            )
            await connection.execute(
                text(
                    f'UPDATE "{self.schemas[0]}".catalog_item SET sku=:sku WHERE id=:id'
                ),
                {"sku": "Legacy Mixed Case", "id": UUID(item)},
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        row = (await self.rows("catalog_item"))[0]
        self.assertIsNone(row["inventory_item_id"])
        self.assertNotIn("sku", row)
        self.assertEqual(await self.rows("inventory_items"), [])

    async def test_concurrent_binding_and_deletion_have_no_dangling_reference(
        self,
    ) -> None:
        """Удаление под блокировкой завершается раньше ожидающего назначения ссылки."""
        response = await self.client.post(
            self.inventory_url,
            headers=self.headers,
            json={"sku": "race", "base_uom": "PCS", "quantity_rules": {"step": "1"}},
        )
        self.assertEqual(response.status_code, 201, response.text)
        inventory_id = response.json()["id"]
        item = await self.create_item()
        locked, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyCatalogItemSku.owner

        async def gated_owner(
            adapter: SqlAlchemyCatalogItemSku, identifier: UUID
        ) -> UUID | None:
            """Приостанавливает проверку после захвата блокировки удаляемого InventoryItem."""
            result = await original(adapter, identifier)
            if str(identifier) == inventory_id and not locked.is_set():
                locked.set()
                await release.wait()
            return result

        with patch.object(SqlAlchemyCatalogItemSku, "owner", gated_owner):
            deleting = asyncio.create_task(
                self.client.delete(
                    f"{self.inventory_url}/{inventory_id}", headers=self.headers
                )
            )
            await asyncio.wait_for(locked.wait(), 3)
            linking = asyncio.create_task(
                self.client.put(
                    f"{self.base}/items/{item}/sku",
                    headers=self.headers,
                    json={"mode": "existing", "inventory_item_id": inventory_id},
                )
            )
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(linking.done())
            finally:
                release.set()
            deleted, linked = await asyncio.wait_for(
                asyncio.gather(deleting, linking), 5
            )
        self.assertEqual(
            (deleted.status_code, linked.status_code),
            (204, 404),
            (deleted.text, linked.text),
        )
        self.assertIsNone((await self.rows("catalog_item"))[0]["inventory_item_id"])
