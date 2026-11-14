"""Создание и чтение партий через HTTP, UoW и реальный PostgreSQL."""

import asyncio
from dataclasses import replace
from datetime import date
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, event, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.repository import (
    SqlAlchemyStockLotRepository,
)
from src.modules.inventory.presentation.stock_lot.router import router as lots_router
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
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


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockLotPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет защиту ссылок, tenant isolation, блокировки и откат общей транзакции."""

    async def asyncSetUp(self) -> None:
        """Создаёт две мигрированные схемы и реальную HTTP-сборку без подмены UoW."""
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], poolclass=NullPool
        )
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schemas = [
            self.naming.schema_name(value) for value in (self.tenant, self.other)
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
        self.app.include_router(lots_router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.items_url = "/api/console/inventory/items"

    async def drop_schemas(self) -> None:
        """Удаляет только две временные схемы текущего теста."""
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )

    async def create_item(
        self, sku: str = "SKU", tracking: str = "LOT", expiration: str = "OPTIONAL"
    ) -> dict[str, str]:
        """Создаёт реальный SKU с явно заданными настройками прослеживаемости."""
        response = await self.client.post(
            self.items_url,
            headers=self.headers,
            json={"sku": sku, "tracking_mode": tracking, "expiration_mode": expiration},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def url(self, item: dict[str, str]) -> str:
        """Возвращает вложенный URL партий по сохранённому UUID товара."""
        return f"{self.items_url}/{item['id']}/lots"

    async def test_create_list_card_exact_number_and_calendar_dates(self) -> None:
        """Полный HTTP-путь сохраняет номер и date, включая отсутствие обеих дат."""
        item = await self.create_item()
        url = self.url(item)
        for number in ("000Lot-a", "000LOT-A", "000Lot-b"):
            response = await self.client.post(
                url,
                headers=self.headers,
                json={
                    "number": f" {number} ",
                    "manufactured_on": "2024-02-29",
                    "expires_on": "2024-02-29",
                },
            )
            self.assertEqual(response.status_code, 201, response.text)
            card = response.json()
            self.assertEqual(card["number"], number)
            self.assertEqual(card["manufactured_on"], "2024-02-29")
            self.assertEqual(card["expires_on"], "2024-02-29")
            self.assertEqual(card["inventory_item_id"], item["id"])
            self.assertEqual(
                (await self.client.get(f"{url}/{card['id']}")).json(), card
            )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            rows = (
                (await connection.execute(select(StockLotModel.manufactured_on)))
                .scalars()
                .all()
            )
            self.assertEqual(rows, [date(2024, 2, 29)] * 3)
        page = (
            await self.client.get(
                url, params={"search": "lot", "offset": 1, "limit": 1}
            )
        ).json()
        self.assertEqual((page["total"], page["offset"], page["limit"]), (3, 1, 1))
        self.assertEqual(page["items"][0]["number"], "000Lot-a")
        response = await self.client.post(
            url, headers=self.headers, json={"number": "empty"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()["manufactured_on"])
        self.assertIsNone(response.json()["expires_on"])

    async def test_unique_number_within_sku_and_literal_search(self) -> None:
        """Точная уникальность не зависит от регистра; символы LIKE ищутся буквально."""
        first = await self.create_item()
        second = await self.create_item("OTHER")
        for item in (first, second):
            response = await self.client.post(
                self.url(item), headers=self.headers, json={"number": "00A_%"}
            )
            self.assertEqual(response.status_code, 201, response.text)
        response = await self.client.post(
            self.url(first), headers=self.headers, json={"number": " 00A_% "}
        )
        self.assertEqual(response.status_code, 409, response.text)
        for number in ("00a_%", "00AXX", "МояПартия"):
            response = await self.client.post(
                self.url(first), headers=self.headers, json={"number": number}
            )
            self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            (await self.client.get(self.url(first), params={"search": "_%"})).json()[
                "total"
            ],
            2,
        )
        self.assertEqual(
            (await self.client.get(self.url(first), params={"search": "моя"})).json()[
                "total"
            ],
            1,
        )
        self.assertEqual(
            (await self.client.get(self.url(first), params={"offset": 100})).json()[
                "items"
            ],
            [],
        )

    async def test_tracking_and_expiration_matrix(self) -> None:
        """Создание применяет актуальные политики Domain, REQUIRED допускает неполную карточку."""
        for tracking in ("NONE", "LOT", "SERIAL", "LOT_AND_SERIAL"):
            for expiration in ("NONE", "OPTIONAL", "REQUIRED"):
                if tracking == "NONE" and expiration == "REQUIRED":
                    continue
                item = await self.create_item(
                    f"{tracking}-{expiration}", tracking, expiration
                )
                for filled in (False, True):
                    payload = {"number": str(filled), "manufactured_on": "2020-01-01"}
                    if filled:
                        payload["expires_on"] = "2020-01-01"
                    response = await self.client.post(
                        self.url(item), headers=self.headers, json=payload
                    )
                    allowed = tracking in ("LOT", "LOT_AND_SERIAL") and not (
                        expiration == "NONE" and filled
                    )
                    self.assertEqual(
                        response.status_code, 201 if allowed else 422, response.text
                    )

    async def test_request_dates_types_extra_fields_and_invalid_values(self) -> None:
        """Presentation отклоняет coercion и datetime, Domain — неверные номер и порядок дат."""
        item = await self.create_item()
        payloads = [
            {},
            {"number": 1},
            {"number": None},
            {"number": ""},
            {"number": "  "},
            {"number": "A\u200b"},
            {"number": "A", "id": str(uuid4())},
            {"number": "A", "inventory_item_id": item["id"]},
            {"number": "A", "manufactured_on": "2024-02-30"},
            {"number": "A", "manufactured_on": "2024-2-01"},
            {"number": "A", "manufactured_on": "2024-01-01T00:00:00Z"},
            {"number": "A", "expires_on": 1700000000},
            {
                "number": "A",
                "manufactured_on": "2025-01-02",
                "expires_on": "2025-01-01",
            },
        ]
        for payload in payloads:
            response = await self.client.post(
                self.url(item), headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 422, (payload, response.text))
        self.assertEqual((await self.client.get(self.url(item))).json()["total"], 0)
        for params in (
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"offset": 2147483648},
        ):
            self.assertEqual(
                (await self.client.get(self.url(item), params=params)).status_code, 422
            )

    async def test_missing_owner_wrong_parent_and_tenant_isolation(self) -> None:
        """Отсутствие SKU отличается от пустой страницы; ID партии не раскрывает чужие данные."""
        item = await self.create_item()
        other_item = await self.create_item("OTHER")
        self.assertEqual((await self.client.get(self.url(item))).json()["items"], [])
        created = await self.client.post(
            self.url(item), headers=self.headers, json={"number": "000A"}
        )
        card = created.json()
        for owner in (other_item, {"id": str(uuid4())}):
            self.assertEqual(
                (await self.client.get(f"{self.url(owner)}/{card['id']}")).status_code,
                404,
            )
        missing = {"id": str(uuid4())}
        self.assertEqual((await self.client.get(self.url(missing))).status_code, 404)
        self.assertEqual(
            (
                await self.client.post(
                    self.url(missing), headers=self.headers, json={"number": "A"}
                )
            ).status_code,
            404,
        )
        self.app.state.test_context = replace(
            self.context,
            principal=Principal(str(uuid4()), str(self.other), "session", ("member",)),
        )
        try:
            self.assertEqual((await self.client.get(self.url(item))).status_code, 404)
            self.assertEqual(
                (await self.client.get(f"{self.url(item)}/{card['id']}")).status_code,
                404,
            )
            second = await self.create_item("SKU")
            self.assertEqual(
                (
                    await self.client.post(
                        self.url(second), headers=self.headers, json={"number": "000A"}
                    )
                ).status_code,
                201,
            )
        finally:
            self.app.state.test_context = self.context

    async def test_saved_lots_readable_after_tracking_change(self) -> None:
        """Чтение не переоценивает историческую партию по текущим настройкам товара."""
        item = await self.create_item()
        card = (
            await self.client.post(
                self.url(item), headers=self.headers, json={"number": "A"}
            )
        ).json()
        changed = await self.client.patch(
            f"{self.items_url}/{item['id']}",
            headers=self.headers,
            json={"tracking_mode": "NONE"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(
            (await self.client.get(f"{self.url(item)}/{card['id']}")).json(), card
        )
        self.assertEqual((await self.client.get(self.url(item))).json()["total"], 1)
        self.assertEqual(
            (
                await self.client.post(
                    self.url(item), headers=self.headers, json={"number": "B"}
                )
            ).status_code,
            422,
        )

    async def test_item_deletion_business_guard_and_defensive_fk(self) -> None:
        """SKU с партией защищён доменным запретом до SQL и реальным FK от обхода проверки."""
        item = await self.create_item()
        response = await self.client.post(
            self.url(item), headers=self.headers, json={"number": "A"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
            SqlAlchemyInventoryItemRepository,
        )
        from src.modules.inventory.infrastructure.inventory_item.persistence.usage import (
            SqlAlchemyInventoryItemUsage,
        )
        from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
            InventoryItemModel,
        )

        with patch.object(
            SqlAlchemyInventoryItemRepository, "delete", autospec=True
        ) as deletion:
            response = await self.client.delete(
                f"{self.items_url}/{item['id']}", headers=self.headers
            )
            self.assertEqual(response.status_code, 409, response.text)
            deletion.assert_not_called()
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    delete(InventoryItemModel).where(
                        InventoryItemModel.id == UUID(item["id"])
                    )
                )
        with patch.object(
            SqlAlchemyInventoryItemUsage,
            "get",
            AsyncMock(return_value=InventoryItemDeletionUsage(False)),
        ):
            response = await self.client.delete(
                f"{self.items_url}/{item['id']}", headers=self.headers
            )
            self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.client.get(self.url(item))).json()["total"], 1)

    async def test_concurrent_duplicate_number_is_atomic(self) -> None:
        """Параллельные POST создают ровно одну партию и один ожидаемый конфликт."""
        item = await self.create_item()
        results = await asyncio.gather(
            *[
                self.client.post(
                    self.url(item), headers=self.headers, json={"number": "000A"}
                )
                for _ in range(2)
            ]
        )
        self.assertEqual(sorted(row.status_code for row in results), [201, 409])
        self.assertEqual((await self.client.get(self.url(item))).json()["total"], 1)

    async def test_create_waits_for_latest_item_settings_and_delete(self) -> None:
        """После ожидания блокировки создание видит новые настройки либо отсутствие SKU."""
        from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
            InventoryItemModel,
        )
        from sqlalchemy import update

        for remove in (False, True):
            item = await self.create_item(f"RACE-{remove}")
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    select(InventoryItemModel.id)
                    .where(InventoryItemModel.id == UUID(item["id"]))
                    .with_for_update()
                )
                from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
                    SqlAlchemyInventoryItemRepository,
                )

                attempted = asyncio.Event()
                original = SqlAlchemyInventoryItemRepository.get_for_update

                async def reading(
                    repository: SqlAlchemyInventoryItemRepository,
                    identifier: InventoryItemIdVO,
                ) -> InventoryItem | None:
                    """Сигнализирует попытку чтения до реального ожидающего SELECT."""
                    attempted.set()
                    return await original(repository, identifier)

                task = None
                with patch.object(
                    SqlAlchemyInventoryItemRepository, "get_for_update", reading
                ):
                    try:
                        task = asyncio.create_task(
                            self.client.post(
                                self.url(item),
                                headers=self.headers,
                                json={"number": "A"},
                            )
                        )
                        await asyncio.wait_for(attempted.wait(), 10)
                        if remove:
                            await connection.execute(
                                delete(InventoryItemModel).where(
                                    InventoryItemModel.id == UUID(item["id"])
                                )
                            )
                        else:
                            await connection.execute(
                                update(InventoryItemModel)
                                .where(InventoryItemModel.id == UUID(item["id"]))
                                .values(tracking_mode="NONE")
                            )
                        await connection.commit()
                        response = await asyncio.wait_for(task, 10)
                        self.assertEqual(
                            response.status_code, 404 if remove else 422, response.text
                        )
                    finally:
                        if task is not None and not task.done():
                            task.cancel()
                            await asyncio.gather(task, return_exceptions=True)

    async def test_write_commit_failures_roll_back_and_security(self) -> None:
        """Запись и commit не выдают ложный 201; auth и CSRF закрывают сценарий."""
        item = await self.create_item()
        original = SqlAlchemyStockLotRepository.add

        async def fail(repository: SqlAlchemyStockLotRepository, lot: StockLot) -> None:
            """Прерывает процесс после фактического INSERT."""
            await original(repository, lot)
            raise RuntimeError("write failed")

        with patch.object(SqlAlchemyStockLotRepository, "add", fail):
            self.assertEqual(
                (
                    await self.client.post(
                        self.url(item), headers=self.headers, json={"number": "A"}
                    )
                ).status_code,
                500,
            )

        def fail_commit(session: Session) -> None:
            """Прерывает commit общей транзакции."""
            raise RuntimeError("commit failed")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.client.post(
                    self.url(item), headers=self.headers, json={"number": "B"}
                )
                self.assertEqual(response.status_code, 500, response.text)
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual((await self.client.get(self.url(item))).json()["total"], 0)
        for headers in (
            {},
            {**self.headers, "Origin": "https://outside.example"},
            {**self.headers, "X-CSRF-Token": "bad"},
        ):
            self.assertEqual(
                (
                    await self.client.post(
                        self.url(item), headers=headers, json={"number": "C"}
                    )
                ).status_code,
                403,
            )
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(self.url(item))).status_code, 401)
        self.app.state.test_context = replace(
            self.context,
            principal=Principal(str(uuid4()), None, "session", ("member",)),
        )
        self.assertEqual((await self.client.get(self.url(item))).status_code, 403)

    async def test_migration_constraints_downgrade_and_registration(self) -> None:
        """Metadata и миграция согласованы; CHECK и downgrade защищают/сохраняют данные SKU."""
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
            TenantBase,
        )

        self.assertIn("tenant.stock_lots", TenantBase.metadata.tables)
        item = await self.create_item()
        for values in (
            {"number": " "},
            {
                "number": "X",
                "manufactured_on": date(2025, 1, 2),
                "expires_on": date(2025, 1, 1),
            },
        ):
            with self.assertRaises(IntegrityError):
                async with self.engine.begin() as connection:
                    await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                    await connection.execute(
                        insert(StockLotModel).values(
                            id=uuid4(), inventory_item_id=UUID(item["id"]), **values
                        )
                    )
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0021_inventory_item_packagings"
            )
            self.assertIsNone(
                await connection.scalar(
                    text("SELECT to_regclass(:table)"),
                    {"table": f"{self.schemas[0]}.stock_lots"},
                )
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual((await self.client.get(self.url(item))).status_code, 200)
