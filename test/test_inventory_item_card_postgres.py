"""Полная карточка SKU: атомарное изменение идентичности и дочернего состава через HTTP."""

import os
import unittest

from test import test_inventory_item_packaging_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class InventoryItemCardPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет совместные PATCH/DELETE и сохранность независимых справочников."""

    drop_schemas = support.ItemPackagingPostgresTests.drop_schemas
    create = support.ItemPackagingPostgresTests.create

    async def asyncSetUp(self) -> None:
        """Создаёт товар с двумя штрихкодами, упаковками и самостоятельным типом тары."""
        await support.ItemPackagingPostgresTests.asyncSetUp(self)
        self.packagings = []
        for code in ("BOX", "CAN"):
            response = await self.create(code)
            self.assertEqual(response.status_code, 201, response.text)
            self.packagings.append(response.json())

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
