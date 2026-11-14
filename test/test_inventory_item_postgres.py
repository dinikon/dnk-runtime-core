from src.modules.inventory.infrastructure.inventory_item.catalog_usage import (
    CatalogInventoryItemUsage,
)
from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.handler import (
    FindInventoryItemUsageHandler,
)
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku

"""Срез InventoryItem в двух tenant-схемах одноразовой PostgreSQL базы."""

import asyncio
from dataclasses import replace
from decimal import Decimal
import os
from typing import Any
import unittest
from uuid import uuid4

from httpx import ASGITransport, AsyncClient, Response
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.inventory_item.command.create_inventory_item.command import (
    CreateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.create_inventory_item.handler import (
    CreateInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.command import (
    UpdateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.handler import (
    UpdateInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.command import (
    DeleteInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.handler import (
    DeleteInventoryItemHandler,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemBarcodeAlreadyExistsError,
    InventoryItemSkuAlreadyExistsError,
    InventoryItemNotFoundError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.inventory_item_support import inventory_item_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class InventoryItemPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет ограничения, транзакции, проекции и tenant-миграцию."""

    async def asyncSetUp(self) -> None:
        """Создаёт две независимые схемы штатными tenant-миграциями."""
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schemas = [
            self.naming.schema_name(tenant) for tenant in (self.tenant, self.other)
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
        self.app = inventory_item_app(
            self.sessions, self.context, scoped_connection=True
        )
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = "/api/console/inventory/items"

    async def drop_schemas(self) -> None:
        """Удаляет только созданные этим тестом схемы."""
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )

    async def rows(
        self, table: sa.Table, tenant: EntityIdVO | None = None
    ) -> list[dict[str, Any]]:
        """Читает строки выбранного tenant для проверки сохранённого состояния."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(
                connection, (tenant or self.tenant).uuid, self.naming
            )
            result = await connection.execute(sa.select(table))
            return [dict(row) for row in result.mappings()]

    async def create(
        self, sku: str, barcodes: list[str] | None = None, step: str = "0.001"
    ) -> Response:
        """Создаёт позицию через HTTP и внешний UoW."""
        return await self.client.post(
            self.url,
            headers=self.headers,
            json={
                "sku": sku,
                "base_uom": "KG",
                "quantity_rules": {"step": step},
                "barcodes": barcodes or [],
            },
        )

    async def test_http_round_trip_exact_decimal_barcodes_and_tenant_isolation(
        self,
    ) -> None:
        """Сохраняет точный шаг, дочерние ID и одинаковые коды в разных tenant."""
        step = "0.123456789012345678901234567890123456789"
        response = await self.create(" Straße-01 ", [" 000AbC ", "000abc"], step)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["sku"], "strasse-01")
        detail = await self.client.get(f"{self.url}/{body['id']}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json(), body)
        stored = (await self.rows(InventoryItemModel.__table__))[0]
        self.assertEqual(stored["quantity_step"], Decimal(step))
        barcodes = sorted(
            await self.rows(ItemBarcodeModel.__table__), key=lambda row: row["position"]
        )
        self.assertEqual([row["barcode"] for row in barcodes], ["000AbC", "000abc"])
        self.assertEqual(
            [str(row["id"]) for row in barcodes],
            [row["id"] for row in body["barcodes"]],
        )
        self.assertEqual(await self.rows(InventoryItemModel.__table__, self.other), [])
        listing = (await self.client.get(self.url)).json()
        self.assertEqual(
            Decimal(listing["items"][0]["quantity_rules"]["step"]), Decimal(step)
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(self.url)).json()["total"], 0)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{body['id']}")).status_code, 404
        )
        duplicate_in_other = await self.create("STRASSE-01", ["000AbC", "000abc"], step)
        self.assertEqual(duplicate_in_other.status_code, 201, duplicate_in_other.text)
        self.assertEqual(len(await self.rows(InventoryItemModel.__table__)), 1)
        self.assertEqual(
            len(await self.rows(InventoryItemModel.__table__, self.other)), 1
        )

    async def test_conflicts_rollback_root_and_all_child_inserts(self) -> None:
        """Конфликт штрихкода не оставляет позицию или часть её штрихкодов."""
        self.assertEqual((await self.create("Original", ["occupied"])).status_code, 201)
        self.assertEqual(
            (await self.create(" ORIGINAL ", ["new-code"])).status_code, 409
        )
        response = await self.create("Other", ["free-code", "occupied"])
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            [row["sku"] for row in await self.rows(InventoryItemModel.__table__)],
            ["original"],
        )
        self.assertEqual(
            [row["barcode"] for row in await self.rows(ItemBarcodeModel.__table__)],
            ["occupied"],
        )
        reused = await self.create("Other", ["free-code"])
        self.assertEqual(reused.status_code, 201, reused.text)

    async def test_locked_reads_refresh_models_already_loaded_in_session(self) -> None:
        """Блокировка восстанавливает актуальный агрегат поверх ранее загруженных ORM-моделей."""
        created = (await self.create("cached", ["cached-barcode"])).json()
        identifier = InventoryItemIdVO.from_value(created["id"])
        for by_sku in (False, True):
            with self.subTest(by_sku=by_sku):
                async with self.engine.connect() as connection:
                    await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                    async with self.sessions(bind=connection) as session:
                        cached_root = await session.get(
                            InventoryItemModel, identifier.uuid
                        )
                        self.assertIsNotNone(cached_root)
                        cached_children = (
                            await session.scalars(
                                sa.select(ItemBarcodeModel).where(
                                    ItemBarcodeModel.inventory_item_id
                                    == identifier.uuid
                                )
                            )
                        ).all()
                        self.assertEqual(len(cached_children), 1)
                        sku, barcode = (
                            f"fresh-{int(by_sku)}",
                            f"fresh-barcode-{int(by_sku)}",
                        )
                        async with self.engine.begin() as writer:
                            await bind_tenant_schema(
                                writer, self.tenant.uuid, self.naming
                            )
                            await writer.execute(
                                sa.update(InventoryItemModel)
                                .where(InventoryItemModel.id == identifier.uuid)
                                .values(sku=sku)
                            )
                            await writer.execute(
                                sa.update(ItemBarcodeModel)
                                .where(ItemBarcodeModel.id == cached_children[0].id)
                                .values(barcode=barcode)
                            )
                        repository = SqlAlchemyInventoryItemRepository(session)
                        restored = (
                            await repository.get_by_sku_for_update(SkuVO(sku))
                            if by_sku
                            else await repository.get_for_update(identifier)
                        )
                        self.assertIsNotNone(restored)
                        self.assertEqual(restored.sku.value, SkuVO(sku).value)
                        self.assertEqual(restored.barcodes[0].barcode.value, barcode)
                        self.assertEqual(
                            str(restored.barcodes[0].id), created["barcodes"][0]["id"]
                        )

    async def test_minimal_creation_persists_defaults_and_explicit_values(self) -> None:
        """Создаёт по одному SKU и сохраняет независимые переопределения настроек."""
        for code, settings, expected in (
            ("default", {}, ("PCS", Decimal("1"), "NONE", "NONE")),
            ("mass", {"base_uom": "KG"}, ("KG", Decimal("1"), "NONE", "NONE")),
            (
                "serial",
                {"tracking_mode": "LOT_AND_SERIAL", "expiration_mode": "REQUIRED"},
                ("PCS", Decimal("1"), "LOT_AND_SERIAL", "REQUIRED"),
            ),
        ):
            response = await self.client.post(
                self.url, headers=self.headers, json={"sku": code, **settings}
            )
            self.assertEqual(response.status_code, 201, response.text)
            value = response.json()
            detail = await self.client.get(f"{self.url}/{value['id']}")
            self.assertEqual(detail.json(), value)
            stored = next(
                row
                for row in await self.rows(InventoryItemModel.__table__)
                if row["sku"] == code
            )
            self.assertEqual(
                (
                    stored["base_uom"],
                    stored["quantity_step"],
                    stored["tracking_mode"],
                    stored["expiration_mode"],
                ),
                expected,
            )
            self.assertEqual(value["barcodes"], [])
        duplicate = await self.client.post(
            self.url, headers=self.headers, json={"sku": " DEFAULT "}
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(len(await self.rows(InventoryItemModel.__table__)), 3)

    async def test_list_search_pagination_and_literal_wildcards(self) -> None:
        """Проверяет SQL-фильтры, Unicode casefold, порядок и пустую страницу."""
        for sku in ("zeta", "BETA", "alpha", "x%_y", "Straße"):
            self.assertEqual((await self.create(sku)).status_code, 201)
        page = (
            await self.client.get(self.url, params={"offset": 1, "limit": 2})
        ).json()
        self.assertEqual(page["total"], 5)
        self.assertEqual([row["sku"] for row in page["items"]], ["beta", "strasse"])
        for search, expected in (
            (" STRAẞE ", ["strasse"]),
            ("%_", ["x%_y"]),
            ("absent", []),
        ):
            found = (await self.client.get(self.url, params={"search": search})).json()
            self.assertEqual([row["sku"] for row in found["items"]], expected)
            self.assertEqual(found["total"], len(expected))
        empty_page = (await self.client.get(self.url, params={"offset": 100})).json()
        self.assertEqual((empty_page["items"], empty_page["total"]), ([], 5))

    async def write_concurrently(
        self, commands: tuple[CreateInventoryItemCommand, ...]
    ) -> list[str]:
        """Запускает независимые транзакции после общей точки синхронизации."""
        barrier = asyncio.Barrier(len(commands))

        async def write(command: CreateInventoryItemCommand) -> str:
            """Возвращает наблюдаемый исход отдельной транзакции создания."""
            try:
                async with self.engine.connect() as connection:
                    await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                    async with UnitOfWork(
                        async_sessionmaker(connection, expire_on_commit=False)
                    ) as uow:
                        handler = CreateInventoryItemHandler(
                            SqlAlchemyInventoryItemRepository(uow.session),
                            UUID7Generator(),
                        )
                        await barrier.wait()
                        await handler.execute(command)
                return "created"
            except InventoryItemSkuAlreadyExistsError:
                return "sku_conflict"
            except InventoryItemBarcodeAlreadyExistsError:
                return "barcode_conflict"

        return await asyncio.wait_for(
            asyncio.gather(*(write(command) for command in commands)), timeout=15
        )

    async def test_concurrent_sku_conflict_is_atomic(self) -> None:
        """Канонически равные SKU создают ровно одну позицию при конкуренции."""
        commands = tuple(
            CreateInventoryItemCommand(sku, "PCS", Decimal("1"))
            for sku in ("Straße", " STRASSE ")
        )
        self.assertCountEqual(
            await self.write_concurrently(commands), ["created", "sku_conflict"]
        )
        self.assertEqual(len(await self.rows(InventoryItemModel.__table__)), 1)

    async def test_concurrent_barcode_conflict_rolls_back_losing_root(self) -> None:
        """Общий штрихкод не может принадлежать двум новым позициям."""
        commands = tuple(
            CreateInventoryItemCommand(
                sku, "PCS", Decimal("1"), barcodes=("000shared",)
            )
            for sku in ("one", "two")
        )
        self.assertCountEqual(
            await self.write_concurrently(commands), ["created", "barcode_conflict"]
        )
        self.assertEqual(len(await self.rows(InventoryItemModel.__table__)), 1)
        self.assertEqual(len(await self.rows(ItemBarcodeModel.__table__)), 1)

    async def test_migration_downgrade_and_upgrade(self) -> None:
        """Откатывает только новую ревизию и повторно создаёт таблицы среза."""
        migrator = TenantMigrator()
        async with self.engine.begin() as connection:
            await migrator.downgrade(
                connection, self.schemas[0], "0016_channels_connections_only"
            )
            tables = await connection.run_sync(
                lambda sync: sa.inspect(sync).get_table_names(schema=self.schemas[0])
            )
            self.assertNotIn("inventory_items", tables)
            self.assertIn("companies", tables)
            await migrator.upgrade(connection, self.schemas[0])
        response = await self.create("after-upgrade", ["0001"])
        self.assertEqual(response.status_code, 201, response.text)

    async def test_update_reorders_preserves_ids_and_supports_noop(self) -> None:
        """Сохраняет идентичность детей при перестановке и повторном одинаковом PUT."""
        created = (await self.create("original", ["a", "b"])).json()
        url = f'{self.url}/{created["id"]}'
        payload = dict(
            sku="changed",
            base_uom="PCS",
            quantity_rules={"step": "1"},
            tracking_mode="SERIAL",
            expiration_mode="OPTIONAL",
            barcodes=["b", "a"],
        )
        updated = await self.client.put(url, headers=self.headers, json=payload)
        self.assertEqual(updated.status_code, 200, updated.text)
        body = updated.json()
        self.assertEqual(
            [child["id"] for child in body["barcodes"]],
            [child["id"] for child in reversed(created["barcodes"])],
        )
        repeated = await self.client.put(url, headers=self.headers, json=payload)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json(), body)
        changed = await self.client.patch(
            url, headers=self.headers, json={"sku": "renamed"}
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        cleared = await self.client.patch(
            url, headers=self.headers, json={"barcodes": []}
        )
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(cleared.json()["barcodes"], [])
        self.assertEqual(await self.rows(ItemBarcodeModel.__table__), [])

    async def test_update_conflict_restores_root_and_children(self) -> None:
        """Конфликт после UPDATE и DELETE детей откатывает весь агрегат."""
        original = (await self.create("original", ["own"])).json()
        self.assertEqual((await self.create("occupied", ["taken"])).status_code, 201)
        roots_before = sorted(
            await self.rows(InventoryItemModel.__table__), key=lambda row: row["sku"]
        )
        children_before = sorted(
            await self.rows(ItemBarcodeModel.__table__), key=lambda row: row["barcode"]
        )
        url = f'{self.url}/{original["id"]}'
        for payload in (
            {"sku": " OCCUPIED "},
            {"sku": "renamed", "barcodes": ["free", "taken"]},
        ):
            response = await self.client.patch(url, headers=self.headers, json=payload)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(
                sorted(
                    await self.rows(InventoryItemModel.__table__),
                    key=lambda row: row["sku"],
                ),
                roots_before,
            )
            self.assertEqual(
                sorted(
                    await self.rows(ItemBarcodeModel.__table__),
                    key=lambda row: row["barcode"],
                ),
                children_before,
            )

    async def test_delete_cascades_only_owned_barcodes_and_isolates_tenants(
        self,
    ) -> None:
        """Удаляет только собственных детей; чужой tenant видит 404 по тому же ID."""
        original = (await self.create("original", ["own"])).json()
        other = (await self.create("other", ["other-code"])).json()
        url = f'{self.url}/{original["id"]}'
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        foreign_delete = await self.client.delete(
            url,
            headers=self.headers,
        )
        self.assertEqual(foreign_delete.status_code, 404, foreign_delete.text)
        foreign_patch = await self.client.patch(
            url, headers=self.headers, json={"sku": "foreign"}
        )
        self.assertEqual(foreign_patch.status_code, 404, foreign_patch.text)
        self.app.state.test_context = self.context
        deleted = await self.client.delete(
            url,
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(
            [str(row["id"]) for row in await self.rows(InventoryItemModel.__table__)],
            [other["id"]],
        )
        self.assertEqual(
            [row["barcode"] for row in await self.rows(ItemBarcodeModel.__table__)],
            ["other-code"],
        )
        self.assertEqual(
            (
                await self.client.delete(
                    url,
                    headers=self.headers,
                )
            ).status_code,
            404,
        )
        self.assertEqual((await self.create("original", ["own"])).status_code, 201)

    async def mutate_concurrently(
        self,
        commands: tuple[UpdateInventoryItemCommand | DeleteInventoryItemCommand, ...],
    ) -> list[str]:
        """Запускает реальные конкурирующие сценарии на отдельных соединениях."""
        barrier = asyncio.Barrier(len(commands))

        async def mutate(
            command: UpdateInventoryItemCommand | DeleteInventoryItemCommand,
        ) -> str:
            """Возвращает исход команды после завершения её собственного UoW."""
            try:
                async with self.engine.connect() as connection:
                    await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                    async with UnitOfWork(
                        async_sessionmaker(connection, expire_on_commit=False)
                    ) as uow:
                        repository = SqlAlchemyInventoryItemRepository(uow.session)
                        await barrier.wait()
                        if isinstance(command, UpdateInventoryItemCommand):
                            await UpdateInventoryItemHandler(
                                repository, UUID7Generator()
                            ).execute(command)
                            outcome = "updated"
                        else:
                            await DeleteInventoryItemHandler(
                                repository,
                                CatalogInventoryItemUsage(
                                    FindInventoryItemUsageHandler(
                                        SqlAlchemyCatalogItemSku(uow.session)
                                    )
                                ),
                            ).execute(command)
                            outcome = "deleted"
                return outcome
            except InventoryItemNotFoundError:
                return "not_found"

        return await asyncio.wait_for(
            asyncio.gather(*(mutate(command) for command in commands)), timeout=15
        )

    async def test_concurrent_patches_preserve_independent_changes(self) -> None:
        """Блокировка корня сохраняет изменения разных полей двух конкурентных PATCH."""
        created = (await self.create("original", ["own"])).json()
        identifier = InventoryItemIdVO.from_value(created["id"])
        commands = (
            UpdateInventoryItemCommand(identifier, frozenset({"sku"}), sku="renamed"),
            UpdateInventoryItemCommand(
                identifier, frozenset({"barcodes"}), barcodes=("new",)
            ),
        )
        self.assertEqual(
            await self.mutate_concurrently(commands), ["updated", "updated"]
        )
        rows = await self.rows(InventoryItemModel.__table__)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sku"], "renamed")
        self.assertEqual(
            [row["barcode"] for row in await self.rows(ItemBarcodeModel.__table__)],
            ["new"],
        )

    async def test_update_delete_race_does_not_resurrect_deleted_item(self) -> None:
        """Удаление выигрывает итог гонки, обновление отсутствующего корня не выполняет upsert."""
        created = (await self.create("original", ["own"])).json()
        identifier = InventoryItemIdVO.from_value(created["id"])
        results = await self.mutate_concurrently(
            (
                UpdateInventoryItemCommand(
                    identifier, frozenset({"sku"}), sku="updated"
                ),
                DeleteInventoryItemCommand(identifier),
            )
        )
        self.assertIn(results, (["updated", "deleted"], ["not_found", "deleted"]))
        self.assertEqual(await self.rows(InventoryItemModel.__table__), [])
        self.assertEqual(await self.rows(ItemBarcodeModel.__table__), [])
