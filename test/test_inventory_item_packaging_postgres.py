"""Упаковки: реальный HTTP/UoW, PostgreSQL, миграция, точность и конкурентность."""

import asyncio
from dataclasses import replace
from decimal import Decimal
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4
from httpx import Response
from sqlalchemy import delete, event, insert, inspect, select, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.query import (
    GetItemPackagingQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.item_packaging_query_repository import (
    SqlAlchemyItemPackagingQueryRepository,
)
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)
from src.modules.inventory.presentation.packaging_type.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from test import test_inventory_warehouse_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class ItemPackagingPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет полный путь сценариев на двух изолированных tenant-схемах."""

    drop_schemas = support.WarehousePostgresTests.drop_schemas

    async def asyncSetUp(self) -> None:
        """Поднимает мигрированные tenant и создаёт SKU с независимыми штрихкодами."""
        await support.WarehousePostgresTests.asyncSetUp(self)
        self.app.include_router(router, prefix="/api/console")
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "item", "barcodes": ["0001", "0002"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.item = response.json()
        response = await self.client.post(
            "/api/console/inventory/packaging-types",
            headers=self.headers,
            json={"code": "BOX", "name": "Ящик"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.kind = response.json()
        self.item_url = f"/api/console/inventory/items/{self.item['id']}"
        self.url = f"{self.item_url}/packagings"

    async def create(
        self,
        code: str = "BOX-12",
        quantity: str = "12",
        uom: str = "PCS",
        name: str = "Ящик",
    ) -> Response:
        """Добавляет упаковку через публичный контракт с реальным CSRF."""
        return await self.client.post(
            self.url,
            headers=self.headers,
            json={
                "packaging_type_id": self.kind["id"],
                "code": code,
                "name": name,
                "content_quantity": quantity,
                "content_uom": uom,
            },
        )

    async def test_roundtrip_preserves_exact_decimal_and_ownership(self) -> None:
        """Хранит количество длиннее стандартной точности Decimal без округления или float."""
        value = "12.000000000000000000000000000000000000001"
        response = await self.client.patch(
            self.item_url,
            headers=self.headers,
            json={
                "base_uom": "L",
                "quantity_rules": {"step": "0.000000000000000000000000000000000000001"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.create(" Can-5 ", value, "L", " Канистра ")
        self.assertEqual(response.status_code, 201, response.text)
        card = response.json()
        self.assertEqual(
            (card["code"], card["name"], card["inventory_item_id"]),
            ("Can-5", "Канистра", self.item["id"]),
        )
        self.assertEqual(Decimal(card["content_quantity"]), Decimal(value))
        self.assertIsInstance(card["content_quantity"], str)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{card['id']}")).json(), card
        )
        self.assertEqual(
            (await self.client.get(self.url)).json(),
            {"items": [card], "total": 1, "offset": 0, "limit": 50},
        )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                item = await SqlAlchemyInventoryItemRepository(session).get_for_update(
                    InventoryItemIdVO(UUID(self.item["id"]))
                )
                self.assertIsNotNone(item)
                if item is None:
                    self.fail("Missing item")
                self.assertEqual(
                    item.packagings[0].content_quantity.value, Decimal(value)
                )
                self.assertEqual(
                    [b.barcode.value for b in item.barcodes], ["0001", "0002"]
                )

    async def test_existing_put_patch_preserve_collections_and_revalidate_settings(
        self,
    ) -> None:
        """Обычное изменение корня сохраняет ID/порядок детей и проверяет их совместимость."""
        cards = [(await self.create(code)).json() for code in ("B", "A")]
        for method, payload in [
            ("PATCH", {"sku": "renamed"}),
            (
                "PUT",
                {
                    "sku": "renamed-again",
                    "base_uom": "PCS",
                    "quantity_rules": {"step": "1"},
                    "tracking_mode": "NONE",
                    "expiration_mode": "NONE",
                    "barcodes": ["0001", "0002"],
                },
            ),
        ]:
            response = await self.client.request(
                method, self.item_url, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["barcodes"], self.item["barcodes"])
            self.assertEqual((await self.client.get(self.url)).json()["items"], cards)
        for payload in ({"base_uom": "KG"}, {"quantity_rules": {"step": "5"}}):
            response = await self.client.patch(
                self.item_url, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.client.get(self.url)).json()["items"], cards)
        self.assertEqual(
            (await self.client.get(self.item_url)).json()["quantity_rules"],
            {"step": "1"},
        )

    async def test_exact_code_uniqueness_search_and_pagination(self) -> None:
        """Коды регистрозависимы внутри SKU, поиск буквальный и без учёта регистра."""
        cards = []
        for code, name in [
            ("BOX", "ЯЩИК"),
            ("box", "малый"),
            ("100%_", "спец"),
            ("100xx", "обычный"),
        ]:
            response = await self.create(code, name=name)
            self.assertEqual(response.status_code, 201, response.text)
            cards.append(response.json())
        self.assertEqual((await self.create(" BOX ")).status_code, 409)
        response = await self.client.get(
            self.url, params={"search": " bOx ", "offset": 1, "limit": 1}
        )
        self.assertEqual(
            response.json(), {"items": [cards[1]], "total": 2, "offset": 1, "limit": 1}
        )
        self.assertEqual(
            (await self.client.get(self.url, params={"search": "%_"})).json()["items"],
            [cards[2]],
        )
        self.assertEqual(
            (await self.client.get(self.url, params={"search": "ящик"})).json()[
                "items"
            ],
            [cards[0]],
        )
        response = await self.client.post(
            "/api/console/inventory/items", headers=self.headers, json={"sku": "other"}
        )
        other = response.json()["id"]
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/items/{other}/packagings"
                )
            ).json()["items"],
            [],
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/items/{other}/packagings/{cards[0]['id']}"
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/items/{uuid4()}/packagings"
                )
            ).status_code,
            404,
        )

    async def test_inactive_type_keeps_existing_packaging_readable_and_restorable(
        self,
    ) -> None:
        """Деактивация запрещает новое назначение, сохраняя существующие ссылки."""
        card = (await self.create()).json()
        response = await self.client.patch(
            f"/api/console/inventory/packaging-types/{self.kind['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.create("NEW")).status_code, 409)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{card['id']}")).json(), card
        )
        response = await self.client.patch(
            self.item_url, headers=self.headers, json={"sku": "still-editable"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.client.get(self.url)).json()["items"], [card])

    async def test_concurrent_additions_preserve_both_children_and_reject_duplicate(
        self,
    ) -> None:
        """Блокировка корня не теряет параллельный состав и сериализует проверку кода."""
        results = await asyncio.wait_for(
            asyncio.gather(self.create("A"), self.create("B")), 10
        )
        self.assertEqual(
            [r.status_code for r in results], [201, 201], [r.text for r in results]
        )
        results = await asyncio.wait_for(
            asyncio.gather(self.create("SAME"), self.create(" SAME ")), 10
        )
        self.assertEqual(
            sorted(r.status_code for r in results),
            [201, 409],
            [r.text for r in results],
        )
        rows = (await self.client.get(self.url)).json()["items"]
        self.assertEqual({r["code"] for r in rows}, {"A", "B", "SAME"})
        self.assertEqual(
            (await self.client.get(self.item_url)).json()["barcodes"],
            self.item["barcodes"],
        )

    async def test_assignment_waits_for_type_deactivation_and_rechecks_fresh_state(
        self,
    ) -> None:
        """После ожидания блокировки назначение видит уже неактивный тип тары."""
        task = None
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(PackagingTypeModel)
                .where(PackagingTypeModel.id == UUID(self.kind["id"]))
                .values(is_active=False)
            )
            started = asyncio.Event()
            original = SqlAlchemyInventoryItemRepository.get_for_update

            async def observed(
                repository: SqlAlchemyInventoryItemRepository,
                identifier: InventoryItemIdVO,
            ) -> InventoryItem | None:
                """Сигнализирует, что запрос уже получил блокировку своего корня."""
                result = await original(repository, identifier)
                started.set()
                return result

            try:
                with patch.object(
                    SqlAlchemyInventoryItemRepository, "get_for_update", observed
                ):
                    task = asyncio.create_task(self.create())
                    await asyncio.wait_for(started.wait(), 5)
                    self.assertFalse(task.done())
                    await connection.commit()
                    response = await asyncio.wait_for(task, 5)
                self.assertEqual(response.status_code, 409, response.text)
            finally:
                if task is not None and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((await self.client.get(self.url)).json()["total"], 0)

    async def test_failures_rollback_full_aggregate_and_commit_never_returns_success(
        self,
    ) -> None:
        """Ошибка после записи или при commit сохраняет прежние упаковки и штрихкоды."""
        first = (await self.create("FIRST")).json()
        original = SqlAlchemyInventoryItemRepository.save

        async def fail_after_save(
            repository: SqlAlchemyInventoryItemRepository, item: InventoryItem
        ) -> None:
            """Прерывает процесс после всех INSERT/DELETE без локального rollback."""
            await original(repository, item)
            raise RuntimeError("after save unavailable")

        with patch.object(SqlAlchemyInventoryItemRepository, "save", fail_after_save):
            response = await self.create("SECOND")
        self.assertEqual(response.status_code, 500, response.text)

        def fail_commit(session: Session) -> None:
            """Не позволяет успешно завершить внешний UoW."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.create("THIRD")
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(self.url)).json()["items"], [first])
        self.assertEqual(
            (await self.client.get(self.item_url)).json()["barcodes"],
            self.item["barcodes"],
        )

    async def test_tenant_isolation_and_foreign_ids(self) -> None:
        """ID товара, упаковки и типа другого tenant недоступны, одинаковые коды разрешены."""
        first = (await self.create()).json()
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(self.url)).status_code, 404)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{first['id']}")).status_code, 404
        )
        self.assertEqual((await self.create("OTHER")).status_code, 404)
        response = await self.client.post(
            "/api/console/inventory/items", headers=self.headers, json={"sku": "item"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        other_url = f"/api/console/inventory/items/{response.json()['id']}/packagings"
        payload = {
            "packaging_type_id": self.kind["id"],
            "code": "BOX-12",
            "name": "Ящик",
            "content_quantity": "12",
            "content_uom": "PCS",
        }
        response = await self.client.post(other_url, headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 404, response.text)
        response = await self.client.post(
            "/api/console/inventory/packaging-types",
            headers=self.headers,
            json={"code": "BOX", "name": "Ящик"},
        )
        payload["packaging_type_id"] = response.json()["id"]
        response = await self.client.post(other_url, headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 201, response.text)

    async def test_query_refreshes_identity_map_without_domain_restore(self) -> None:
        """Query читает свежую модель и не вызывает фабрики Domain."""
        card = (await self.create()).json()
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                model = await session.get(ItemPackagingModel, UUID(card["id"]))
                async with self.engine.begin() as other:
                    await bind_tenant_schema(other, self.tenant.uuid, self.naming)
                    await other.execute(
                        update(ItemPackagingModel)
                        .where(ItemPackagingModel.id == UUID(card["id"]))
                        .values(name="Новое название")
                    )
                with patch.object(
                    InventoryItem,
                    "restore",
                    side_effect=AssertionError("Query must not restore Domain"),
                ):
                    result = await SqlAlchemyItemPackagingQueryRepository(
                        session
                    ).get_details(
                        GetItemPackagingQuery(
                            InventoryItemIdVO(UUID(self.item["id"])),
                            ItemPackagingIdVO(UUID(card["id"])),
                        )
                    )
                self.assertIsNotNone(result)
                if result is None:
                    self.fail("Missing projection")
                self.assertEqual(result.name, "Новое название")
                self.assertIsNotNone(model)

    async def test_database_constraints_and_item_cascade(self) -> None:
        """FK и CHECK защищают прямой SQL, CASCADE удаляет только собственных детей."""
        card = (await self.create()).json()
        values = {
            "id": uuid4(),
            "inventory_item_id": UUID(self.item["id"]),
            "packaging_type_id": UUID(self.kind["id"]),
            "code": "DIRECT",
            "name": "Direct",
            "content_quantity": Decimal(12),
            "content_uom": "PCS",
            "position": 1,
        }
        for changes in (
            {"code": " "},
            {"name": " "},
            {"content_uom": " "},
            {"position": -1},
            {"content_quantity": Decimal(0)},
            {"content_quantity": Decimal("NaN")},
            {"content_quantity": Decimal("Infinity")},
            {"content_quantity": Decimal("-Infinity")},
            {"packaging_type_id": uuid4()},
            {"inventory_item_id": uuid4()},
            {"code": "BOX-12"},
            {"position": 0},
        ):
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                with self.assertRaises(IntegrityError):
                    await connection.execute(
                        insert(ItemPackagingModel).values({**values, **changes})
                    )
                await connection.rollback()
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            with self.assertRaises(IntegrityError):
                await connection.execute(
                    delete(PackagingTypeModel).where(
                        PackagingTypeModel.id == UUID(self.kind["id"])
                    )
                )
            await connection.rollback()
        self.assertEqual(
            (await self.client.delete(self.item_url, headers=self.headers)).status_code,
            204,
        )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            self.assertIsNone(
                await connection.scalar(
                    select(ItemPackagingModel.id).where(
                        ItemPackagingModel.id == UUID(card["id"])
                    )
                )
            )
            self.assertIsNone(await connection.scalar(select(ItemBarcodeModel.id)))
            self.assertIsNotNone(await connection.scalar(select(PackagingTypeModel.id)))

    async def test_migration_metadata_downgrade_upgrade(self) -> None:
        """Ревизия совпадает с metadata, откат сохраняет родительские таблицы и данные."""
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)

            def table_names(conn: Connection) -> list[str]:
                """Читает таблицы текущей тестовой tenant-схемы."""
                return inspect(conn).get_table_names(schema=self.schemas[0])

            def constraints(conn: Connection) -> set[str | None]:
                """Собирает имена защитных UNIQUE и FK из реальной БД."""
                inspector = inspect(conn)
                return {
                    c["name"]
                    for c in [
                        *inspector.get_foreign_keys(
                            "inventory_item_packagings", schema=self.schemas[0]
                        ),
                        *inspector.get_unique_constraints(
                            "inventory_item_packagings", schema=self.schemas[0]
                        ),
                    ]
                }

            self.assertEqual(
                await connection.run_sync(constraints),
                {
                    "fk_item_packagings_item",
                    "fk_item_packagings_type",
                    "uq_item_packagings_code",
                    "uq_item_packagings_position",
                },
            )
            self.assertEqual(
                set(
                    migration_metadata()
                    .tables["inventory_item_packagings"]
                    .columns.keys()
                ),
                {
                    "id",
                    "inventory_item_id",
                    "packaging_type_id",
                    "code",
                    "name",
                    "content_quantity",
                    "content_uom",
                    "position",
                },
            )
            migrator = TenantMigrator()
            self.assertEqual(
                await migrator.current(connection, self.schemas[0]), (migrator.head(),)
            )
            await migrator.downgrade(
                connection, self.schemas[0], "0020_inventory_packaging_types"
            )
            self.assertNotIn(
                "inventory_item_packagings", await connection.run_sync(table_names)
            )
            self.assertIn("packaging_types", await connection.run_sync(table_names))
            await migrator.upgrade(connection, self.schemas[0])
        self.assertEqual((await self.client.get(self.item_url)).status_code, 200)
        self.assertEqual((await self.create()).status_code, 201)
