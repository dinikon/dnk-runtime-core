"""DELETE упаковок на настоящем HTTP/UoW с PostgreSQL, блокировками и rollback."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import Response
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)
from src.modules.inventory.presentation.packaging_type.router import (
    router as packaging_type_router,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_item_packaging_postgres as support
from test import test_catalog_inventory_postgres as catalog_support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class DeleteItemPackagingPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет физическое сохранение полного агрегата после удаления дочерней Entity."""

    drop_schemas = support.ItemPackagingPostgresTests.drop_schemas
    create = support.ItemPackagingPostgresTests.create

    async def asyncSetUp(self) -> None:
        """Создаёт два tenant и товар с тремя упаковками и двумя штрихкодами."""
        await support.ItemPackagingPostgresTests.asyncSetUp(self)
        self.cards = []
        for code in ("A", "B", "C"):
            response = await self.create(code)
            self.assertEqual(response.status_code, 201, response.text)
            self.cards.append(response.json())

    async def remove(self, identifier: str) -> Response:
        """Удаляет вариант только в текущем товаре через публичный HTTP-контракт."""
        return await self.client.delete(
            f"{self.url}/{identifier}", headers=self.headers
        )

    async def test_delete_middle_first_and_last_preserves_remaining_ids_order_and_root(
        self,
    ) -> None:
        """Последовательное удаление не затрагивает товар, штрихкоды и самостоятельный тип тары."""
        remaining = self.cards.copy()
        for card in (self.cards[1], self.cards[0], self.cards[2]):
            response = await self.remove(card["id"])
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(response.content, b"")
            remaining = [row for row in remaining if row["id"] != card["id"]]
            self.assertEqual(
                (await self.client.get(self.url)).json(),
                {"items": remaining, "total": len(remaining), "offset": 0, "limit": 50},
            )
            self.assertEqual(
                (await self.client.get(f"{self.url}/{card['id']}")).status_code, 404
            )
            self.assertEqual((await self.client.get(self.item_url)).json(), self.item)
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                statement = (
                    select(ItemPackagingModel.id, ItemPackagingModel.position)
                    .where(
                        ItemPackagingModel.inventory_item_id == UUID(self.item["id"])
                    )
                    .order_by(ItemPackagingModel.position)
                )
                positions = (await connection.execute(statement)).all()
                self.assertEqual(
                    [(str(row[0]), row[1]) for row in positions],
                    [(row["id"], i) for i, row in enumerate(remaining)],
                )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/packaging-types/{self.kind['id']}"
                )
            ).json(),
            self.kind,
        )

    async def test_repeat_missing_parent_and_wrong_owner_are_404_without_changes(
        self,
    ) -> None:
        """Оба идентификатора ограничивают удаление, повтор не превращается в успешный no-op."""
        self.assertEqual((await self.remove(self.cards[0]["id"])).status_code, 204)
        self.assertEqual((await self.remove(self.cards[0]["id"])).status_code, 404)
        self.assertEqual((await self.remove(str(uuid4()))).status_code, 404)
        response = await self.client.post(
            "/api/console/inventory/items", headers=self.headers, json={"sku": "other"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        for owner_id in (response.json()["id"], str(uuid4())):
            response = await self.client.delete(
                f"/api/console/inventory/items/{owner_id}/packagings/{self.cards[1]['id']}",
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"], self.cards[1:]
        )

    async def test_inactive_type_does_not_prevent_deletion(self) -> None:
        """Активность тары не относится к удалению варианта; тип и оставшиеся ссылки сохраняются."""
        response = await self.client.patch(
            f"/api/console/inventory/packaging-types/{self.kind['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.remove(self.cards[0]["id"])
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"], self.cards[1:]
        )
        self.assertEqual((await self.client.get(self.item_url)).json(), self.item)
        self.assertFalse(
            (
                await self.client.get(
                    f"/api/console/inventory/packaging-types/{self.kind['id']}"
                )
            ).json()["is_active"]
        )

    async def test_deleted_code_can_be_reused_with_a_new_identity(self) -> None:
        """Удаление освобождает точный код в товаре и не восстанавливает прежний ID."""
        self.assertEqual((await self.remove(self.cards[0]["id"])).status_code, 204)
        response = await self.create(" A ")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotEqual(response.json()["id"], self.cards[0]["id"])
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"],
            [*self.cards[1:], response.json()],
        )

    async def test_other_tenant_cannot_delete_existing_packaging(self) -> None:
        """UUID другого tenant скрыт; после отказа исходная коллекция остаётся прежней."""
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        response = await self.remove(self.cards[0]["id"])
        self.assertEqual(response.status_code, 404, response.text)
        self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.url)).json()["items"], self.cards)

    async def test_concurrent_deletes_of_same_and_different_children_serialize(
        self,
    ) -> None:
        """У одного удаления есть победитель, разные удаления сохраняются оба без потери состава."""
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.remove(self.cards[0]["id"]), self.remove(self.cards[0]["id"])
            ),
            10,
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [204, 404],
            [r.text for r in responses],
        )
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.remove(self.cards[1]["id"]), self.remove(self.cards[2]["id"])
            ),
            10,
        )
        self.assertEqual(
            [r.status_code for r in responses], [204, 204], [r.text for r in responses]
        )
        self.assertEqual((await self.client.get(self.url)).json()["total"], 0)
        self.assertEqual((await self.client.get(self.item_url)).json(), self.item)

    async def test_waiting_patch_cannot_resurrect_deleted_packaging(self) -> None:
        """PATCH после ожидания блокировки видит удалённую Entity и возвращает 404 без upsert."""
        written = asyncio.Event()
        waiting = asyncio.Event()
        release = asyncio.Event()
        original_save = SqlAlchemyInventoryItemRepository.save
        original_get = SqlAlchemyInventoryItemRepository.get_for_update
        calls = 0

        async def hold_save(
            repository: SqlAlchemyInventoryItemRepository, item: InventoryItem
        ) -> None:
            """Удерживает транзакцию DELETE после реальных SQL-записей до запуска PATCH."""
            await original_save(repository, item)
            written.set()
            await release.wait()

        async def observe_get(
            repository: SqlAlchemyInventoryItemRepository, identifier: InventoryItemIdVO
        ) -> InventoryItem | None:
            """Сигнализирует попытку второго запроса получить уже удерживаемую блокировку."""
            nonlocal calls
            calls += 1
            if calls == 2:
                waiting.set()
            return await original_get(repository, identifier)

        tasks = []
        try:
            with (
                patch.object(SqlAlchemyInventoryItemRepository, "save", hold_save),
                patch.object(
                    SqlAlchemyInventoryItemRepository, "get_for_update", observe_get
                ),
            ):
                deletion = asyncio.create_task(self.remove(self.cards[0]["id"]))
                tasks.append(deletion)
                await asyncio.wait_for(written.wait(), 5)
                update = asyncio.create_task(
                    self.client.patch(
                        f"{self.url}/{self.cards[0]['id']}",
                        headers=self.headers,
                        json={"name": "Не восстанавливать"},
                    )
                )
                tasks.append(update)
                await asyncio.wait_for(waiting.wait(), 5)
                self.assertFalse(update.done())
                release.set()
                deleted, updated = await asyncio.wait_for(asyncio.gather(*tasks), 5)
            self.assertEqual(
                (deleted.status_code, updated.status_code),
                (204, 404),
                (deleted.text, updated.text),
            )
        finally:
            release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"], self.cards[1:]
        )
        self.assertEqual((await self.client.get(self.item_url)).json(), self.item)

    async def test_write_and_commit_failure_roll_back_full_aggregate(self) -> None:
        """Ошибка после DELETE/INSERT детей и ошибка commit не возвращают успешный 204."""
        original = SqlAlchemyInventoryItemRepository.save

        async def fail_after_save(
            repository: SqlAlchemyInventoryItemRepository, item: InventoryItem
        ) -> None:
            """Прерывает процесс после изменения таблиц, оставляя откат внешнему UoW."""
            await original(repository, item)
            raise RuntimeError("after save unavailable")

        with patch.object(SqlAlchemyInventoryItemRepository, "save", fail_after_save):
            response = await self.remove(self.cards[0]["id"])
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(self.url)).json()["items"], self.cards)

        def fail_commit(session: Session) -> None:
            """Не позволяет завершить общую транзакцию после успешного возврата handler."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.remove(self.cards[1]["id"])
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(self.url)).json()["items"], self.cards)
        self.assertEqual((await self.client.get(self.item_url)).json(), self.item)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class LinkedCatalogItemPackagingDeletePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Различает запрет удаления связанного SKU и удаление его дочерней упаковки."""

    asyncSetUpBase = catalog_support.CatalogInventoryPostgresTests.asyncSetUpBase
    asyncTearDown = catalog_support.CatalogInventoryPostgresTests.asyncTearDown
    request = catalog_support.CatalogInventoryPostgresTests.request
    create_item = catalog_support.CatalogInventoryPostgresTests.create_item

    async def asyncSetUp(self) -> None:
        """Собирает настоящие Catalog и Inventory на одном tenant-UoW."""
        await catalog_support.CatalogInventoryPostgresTests.asyncSetUp(self)
        self.app.include_router(packaging_type_router, prefix="/api/console")

    async def test_linked_catalog_sku_keeps_its_link_and_barcodes_after_packaging_delete(
        self,
    ) -> None:
        """Удаление упаковки сохраняет InventoryItem, Catalog FK, штрихкоды и PackagingType."""
        response = await self.client.post(
            self.inventory_url,
            headers=self.headers,
            json={"sku": "linked", "barcodes": ["0001"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        catalog_id = await self.create_item(
            {"mode": "existing", "inventory_item_id": item["id"]}
        )
        response = await self.client.post(
            "/api/console/inventory/packaging-types",
            headers=self.headers,
            json={"code": "BOX", "name": "Ящик"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        kind = response.json()
        item_url = f"{self.inventory_url}/{item['id']}"
        response = await self.client.post(
            f"{item_url}/packagings",
            headers=self.headers,
            json={
                "packaging_type_id": kind["id"],
                "code": "BOX-12",
                "name": "Ящик 12",
                "content_quantity": "12",
                "content_uom": "PCS",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        packaging = response.json()
        self.assertEqual(
            (await self.client.delete(item_url, headers=self.headers)).status_code, 409
        )
        response = await self.client.delete(
            f"{item_url}/packagings/{packaging['id']}", headers=self.headers
        )
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual((await self.client.get(item_url)).json(), item)
        self.assertEqual(
            (await self.client.get(f"{item_url}/packagings")).json()["total"], 0
        )
        catalog = (await self.request("GET", f"/items/{catalog_id}?locale=en"))["item"]
        self.assertEqual(
            (catalog["inventory_item_id"], catalog["sku"]), (item["id"], item["sku"])
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/packaging-types/{kind['id']}"
                )
            ).json(),
            kind,
        )
