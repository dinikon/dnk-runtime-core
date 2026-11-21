"""PUT/PATCH упаковок: полный HTTP-путь и конкурентные изменения в PostgreSQL."""

import asyncio
from dataclasses import replace
from decimal import Decimal
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4
from httpx import Response
from sqlalchemy import event, update
from sqlalchemy.orm import Session
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_item_packaging_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class ItemPackagingMutationsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет изменение Entity в полном агрегате, блокировки и tenant isolation."""

    drop_schemas = support.ItemPackagingPostgresTests.drop_schemas
    create = support.ItemPackagingPostgresTests.create

    async def asyncSetUp(self) -> None:
        """Поднимает реальную HTTP-сборку и сохраняет два варианта упаковки."""
        await support.ItemPackagingPostgresTests.asyncSetUp(self)
        response = await self.create()
        self.assertEqual(response.status_code, 201, response.text)
        self.card = response.json()
        response = await self.create("OTHER")
        self.assertEqual(response.status_code, 201, response.text)
        self.other_card = response.json()
        self.detail_url = f"{self.url}/{self.card['id']}"

    async def edit(self, payload: dict[str, object], method: str = "PATCH") -> Response:
        """Изменяет собственную упаковку с настоящей CSRF-защитой."""
        return await self.client.request(
            method, self.detail_url, headers=self.headers, json=payload
        )

    async def new_kind(self, code: str = "CAN") -> dict[str, str]:
        """Создаёт самостоятельный активный тип тары для переназначения упаковки."""
        response = await self.client.post(
            "/api/console/inventory/packaging-types",
            headers=self.headers,
            json={"code": code, "name": "Канистра"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_put_changes_all_fields_preserving_manual_values_and_other_children(
        self,
    ) -> None:
        """PUT меняет итоговый тип и параметры с прежними ID, порядком и штрихкодами."""
        kind = await self.new_kind()
        payload = {
            "packaging_type_id": kind["id"],
            "code": " ManualCASE ",
            "name": " Ручное имя ",
            "content_quantity": "24",
            "content_uom": "PCS",
        }
        response = await self.edit(payload, "PUT")
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**self.card, **payload, "code": "ManualCASE", "name": "Ручное имя"}
        self.assertEqual(response.json(), expected)
        self.assertEqual((await self.client.get(self.detail_url)).json(), expected)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"],
            [expected, self.other_card],
        )
        self.assertEqual(
            (await self.client.get(self.item_url)).json()["barcodes"],
            self.item["barcodes"],
        )

    async def test_partial_updates_merge_all_fields_and_noop_does_not_save(
        self,
    ) -> None:
        """PATCH сохраняет пропущенные значения, а нормализованный no-op не делает запись."""
        kind = await self.new_kind()
        expected = self.card.copy()
        for payload in (
            {"name": "Новое имя"},
            {"code": "NewCASE"},
            {"content_quantity": "36"},
            {"content_uom": "PCS"},
            {"packaging_type_id": kind["id"]},
        ):
            response = await self.edit(payload)
            self.assertEqual(response.status_code, 200, response.text)
            expected.update(payload)
            self.assertEqual(response.json(), expected)
        with patch.object(
            SqlAlchemyInventoryItemRepository, "save", new_callable=AsyncMock
        ) as save:
            response = await self.edit(
                {"code": " NewCASE ", "content_quantity": "36.00"}
            )
            self.assertEqual(response.status_code, 200, response.text)
            save.assert_not_awaited()
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"],
            [expected, self.other_card],
        )

    async def test_quantity_and_unit_change_atomically_with_exact_conversion(
        self,
    ) -> None:
        """Итоговая пара валидируется вместе без некорректного промежуточного значения."""
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "oil", "base_uom": "L", "quantity_rules": {"step": "0.5"}},
        )
        self.assertEqual(response.status_code, 201, response.text)
        item_url = f"/api/console/inventory/items/{response.json()['id']}"
        payload = {
            "packaging_type_id": self.kind["id"],
            "code": "CAN",
            "name": "Канистра",
            "content_quantity": "1",
            "content_uom": "L",
        }
        response = await self.client.post(
            f"{item_url}/packagings", headers=self.headers, json=payload
        )
        self.assertEqual(response.status_code, 201, response.text)
        url = f"{item_url}/packagings/{response.json()['id']}"
        # Одно 500 L валидно, но одно 1 ML не кратно шагу. Итог 500 ML валиден.
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={"content_quantity": "500", "content_uom": "ML"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (response.json()["content_quantity"], response.json()["content_uom"]),
            ("500", "ML"),
        )
        response = await self.client.patch(
            url, headers=self.headers, json={"content_uom": "L"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["content_quantity"], "500")
        original = (await self.client.get(url)).json()
        for payload in (
            {"content_quantity": "1", "content_uom": "ML"},
            {"content_uom": "KG"},
            {"content_quantity": "0"},
            {"content_quantity": "0.25"},
        ):
            response = await self.client.patch(url, headers=self.headers, json=payload)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual((await self.client.get(url)).json(), original)

    async def test_long_decimal_roundtrip_and_rejection_are_atomic(self) -> None:
        """Содержимое длиннее стандартной точности Decimal хранится без округления."""
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={
                "sku": "precision",
                "base_uom": "KG",
                "quantity_rules": {"step": "0.000000000000000000000000000000000000001"},
            },
        )
        item_url = f"/api/console/inventory/items/{response.json()['id']}"
        response = await self.client.post(
            f"{item_url}/packagings",
            headers=self.headers,
            json={
                "packaging_type_id": self.kind["id"],
                "code": "BAG",
                "name": "Мешок",
                "content_quantity": "1",
                "content_uom": "KG",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        url = f"{item_url}/packagings/{response.json()['id']}"
        value = "12.123456789012345678901234567890123456789"
        response = await self.client.patch(
            url, headers=self.headers, json={"content_quantity": value}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(Decimal(response.json()["content_quantity"]), Decimal(value))
        self.assertEqual((await self.client.get(url)).json(), response.json())

    async def test_inactive_current_or_target_type_rejects_even_noop_but_active_reassignment_works(
        self,
    ) -> None:
        """Редактирование проверяет активность итогового типа при любом наборе полей."""
        kind = await self.new_kind()
        response = await self.client.patch(
            f"/api/console/inventory/packaging-types/{self.kind['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        for payload in (
            {"name": "Новое имя"},
            {"name": self.card["name"]},
            {"packaging_type_id": self.kind["id"]},
        ):
            response = await self.edit(payload)
            self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)
        response = await self.edit({"packaging_type_id": kind["id"]})
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**self.card, "packaging_type_id": kind["id"]}
        self.assertEqual(response.json(), expected)
        response = await self.edit({"packaging_type_id": self.kind["id"]})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.client.get(self.detail_url)).json(), expected)

    async def test_duplicate_codes_conflict_but_case_only_change_is_allowed(
        self,
    ) -> None:
        """Точная уникальность сохраняется внутри товара, а отказ не меняет состав."""
        response = await self.edit({"code": " OTHER ", "name": "Не сохранять"})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"],
            [self.card, self.other_card],
        )
        response = await self.edit({"code": "other"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["code"], "other")
        listed = (await self.client.get(self.url, params={"search": "OTHER"})).json()
        self.assertEqual(listed["total"], 2)

    async def test_missing_wrong_owner_and_other_tenant_are_404_without_upsert(
        self,
    ) -> None:
        """Оба path ID ограничивают запись; чужие корни и типы не раскрываются."""
        payload = {
            key: self.card[key]
            for key in (
                "packaging_type_id",
                "code",
                "name",
                "content_quantity",
                "content_uom",
            )
        }
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "different"},
        )
        other_item_id = response.json()["id"]
        for method in ("PUT", "PATCH"):
            for url in (
                f"{self.url}/{uuid4()}",
                f"/api/console/inventory/items/{uuid4()}/packagings/{self.card['id']}",
                f"/api/console/inventory/items/{other_item_id}/packagings/{self.card['id']}",
            ):
                response = await self.client.request(
                    method, url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 404, response.text)
            response = await self.edit(
                {**payload, "packaging_type_id": str(uuid4())}, method
            )
            self.assertEqual(response.status_code, 404, response.text)
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        other_kind = await self.new_kind("FOREIGN")
        for method in ("PUT", "PATCH"):
            response = await self.edit(payload, method)
            self.assertEqual(response.status_code, 404, response.text)
        self.app.state.test_context = self.context
        response = await self.edit({"packaging_type_id": other_kind["id"]})
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)

    async def test_concurrent_independent_patches_merge_and_code_conflicts_serialize(
        self,
    ) -> None:
        """После ожидания блокировки второй PATCH видит первый; разные дети не теряются."""
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.edit({"name": "Новая тара"}), self.edit({"content_quantity": "24"})
            ),
            10,
        )
        self.assertEqual(
            [r.status_code for r in responses], [200, 200], [r.text for r in responses]
        )
        card = (await self.client.get(self.detail_url)).json()
        self.assertEqual((card["name"], card["content_quantity"]), ("Новая тара", "24"))
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.edit({"code": "SAME"}),
                self.client.patch(
                    f"{self.url}/{self.other_card['id']}",
                    headers=self.headers,
                    json={"code": " SAME "},
                ),
            ),
            10,
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 409],
            [r.text for r in responses],
        )
        rows = (await self.client.get(self.url)).json()["items"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r["id"] for r in rows}), 2)
        self.assertEqual(sum(r["code"] == "SAME" for r in rows), 1)

    async def test_waiting_patch_rechecks_type_after_deactivation(self) -> None:
        """PATCH без смены type ID ждёт блокировку типа и отклоняет уже неактивный снимок."""
        task = None
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(PackagingTypeModel)
                .where(PackagingTypeModel.id == UUID(self.kind["id"]))
                .values(is_active=False)
            )
            reached = asyncio.Event()
            original = SqlAlchemyInventoryItemRepository.get_for_update

            async def observed(
                repository: SqlAlchemyInventoryItemRepository,
                identifier: InventoryItemIdVO,
            ) -> InventoryItem | None:
                """Сигнализирует получение блокировки товара перед чтением типа."""
                result = await original(repository, identifier)
                reached.set()
                return result

            try:
                with patch.object(
                    SqlAlchemyInventoryItemRepository, "get_for_update", observed
                ):
                    task = asyncio.create_task(self.edit({"name": "Позднее изменение"}))
                    await asyncio.wait_for(reached.wait(), 5)
                    self.assertFalse(task.done())
                    await connection.commit()
                    response = await asyncio.wait_for(task, 5)
                self.assertEqual(response.status_code, 409, response.text)
            finally:
                if task is not None and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)

    async def test_waiting_patch_revalidates_content_after_item_settings_change(
        self,
    ) -> None:
        """Ожидающий PATCH проверяет новый шаг товара, а не настройки до блокировки."""
        task = None
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(InventoryItemModel)
                .where(InventoryItemModel.id == UUID(self.item["id"]))
                .values(quantity_step=Decimal(2))
            )
            reached = asyncio.Event()
            original = SqlAlchemyInventoryItemRepository.get_for_update

            async def observed(
                repository: SqlAlchemyInventoryItemRepository,
                identifier: InventoryItemIdVO,
            ) -> InventoryItem | None:
                """Фиксирует попытку загрузки корня под удерживаемой блокировкой."""
                reached.set()
                return await original(repository, identifier)

            try:
                with patch.object(
                    SqlAlchemyInventoryItemRepository, "get_for_update", observed
                ):
                    task = asyncio.create_task(self.edit({"content_quantity": "15"}))
                    await asyncio.wait_for(reached.wait(), 5)
                    self.assertFalse(task.done())
                    await connection.commit()
                    response = await asyncio.wait_for(task, 5)
                self.assertEqual(response.status_code, 422, response.text)
            finally:
                if task is not None and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)
        self.assertEqual(
            (await self.client.get(self.item_url)).json()["quantity_rules"],
            {"step": "2"},
        )

    async def test_write_and_commit_failure_rollback_root_and_all_children(
        self,
    ) -> None:
        """Ни ошибка после записи, ни ошибка commit не дают успешный ответ и частичное состояние."""
        original = SqlAlchemyInventoryItemRepository.save

        async def fail_after_save(
            repository: SqlAlchemyInventoryItemRepository, item: InventoryItem
        ) -> None:
            """Вызывает реальные UPDATE/DELETE/INSERT и прерывает процесс до commit."""
            await original(repository, item)
            raise RuntimeError("after write unavailable")

        with patch.object(SqlAlchemyInventoryItemRepository, "save", fail_after_save):
            response = await self.edit(
                {"name": "Не сохранять", "content_quantity": "24"}
            )
        self.assertEqual(response.status_code, 500, response.text)

        def fail_commit(session: Session) -> None:
            """Отклоняет реальное завершение внешней транзакции."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.edit(
                    {
                        key: self.card[key] if key != "name" else "Не сохранять"
                        for key in (
                            "packaging_type_id",
                            "code",
                            "name",
                            "content_quantity",
                            "content_uom",
                        )
                    },
                    "PUT",
                )
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(
            (await self.client.get(self.url)).json()["items"],
            [self.card, self.other_card],
        )
        self.assertEqual(
            (await self.client.get(self.item_url)).json()["barcodes"],
            self.item["barcodes"],
        )
