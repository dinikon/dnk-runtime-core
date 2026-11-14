"""Создание и чтение партий через HTTP, UoW и реальный PostgreSQL."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import date
import os
from typing import TypedDict
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import event, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
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


class StockLotCard(TypedDict):
    """Описывает проверяемый HTTP-контракт партии для тестовых операций."""

    id: str
    inventory_item_id: str
    number: str
    manufactured_on: str | None
    expires_on: str | None


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockLotMutationsPostgresTests(unittest.IsolatedAsyncioTestCase):
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

    async def create_lot(
        self, item: dict[str, str], number: str = "000Lot-a"
    ) -> StockLotCard:
        """Создаёт партию с датами, которые затем проверяются во всех путях обновления."""
        response = await self.client.post(
            self.url(item),
            headers=self.headers,
            json={
                "number": number,
                "manufactured_on": "2020-01-01",
                "expires_on": "2030-01-01",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def detail_url(self, card: StockLotCard) -> str:
        """Возвращает URL с обоими сохранёнными идентификаторами."""
        return f"{self.items_url}/{card['inventory_item_id']}/lots/{card['id']}"

    async def test_patch_preserves_omitted_put_clears_required_and_identity(
        self,
    ) -> None:
        """PATCH сохраняет пропуски, null очищает дату; REQUIRED допускает неполную карточку."""
        item = await self.create_item(expiration="REQUIRED")
        card = await self.create_lot(item)
        url = self.detail_url(card)
        response = await self.client.patch(
            url, headers=self.headers, json={"expires_on": None}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {**card, "expires_on": None})
        response = await self.client.put(
            url,
            headers=self.headers,
            json={"manufactured_on": None, "expires_on": None},
        )
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**card, "manufactured_on": None, "expires_on": None}
        self.assertEqual(response.json(), expected)
        self.assertEqual((await self.client.get(url)).json(), expected)
        self.assertEqual(
            (await self.client.get(self.url(item))).json()["items"], [expected]
        )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            row = (
                await connection.execute(
                    select(
                        StockLotModel.number,
                        StockLotModel.manufactured_on,
                        StockLotModel.expires_on,
                    )
                )
            ).one()
            self.assertEqual(tuple(row), ("000Lot-a", None, None))

    async def test_invalid_contracts_and_dates_are_atomic(self) -> None:
        """Presentation запрещает скрытое изменение номера/владельца, Domain — неверный порядок дат."""
        card = await self.create_lot(await self.create_item())
        url = self.detail_url(card)
        for method in ("PUT", "PATCH"):
            for extra in (
                {"number": "other"},
                {"id": str(uuid4())},
                {"inventory_item_id": str(uuid4())},
                {"version": 1},
            ):
                response = await self.client.request(
                    method,
                    url,
                    headers=self.headers,
                    json={"manufactured_on": "2021-01-01", "expires_on": None, **extra},
                )
                self.assertEqual(response.status_code, 422, response.text)
            for value in (
                "",
                "2026-1-01",
                "2026-02-30",
                "2026-01-01T00:00:00Z",
                1700000000,
                False,
            ):
                response = await self.client.request(
                    method,
                    url,
                    headers=self.headers,
                    json={"manufactured_on": value, "expires_on": None},
                )
                self.assertEqual(response.status_code, 422, response.text)
            response = await self.client.request(
                method,
                url,
                headers=self.headers,
                json={"manufactured_on": "2026-01-02", "expires_on": "2026-01-01"},
            )
            self.assertEqual(response.status_code, 422, response.text)
        for payload in ({}, {"manufactured_on": None}, {"expires_on": None}):
            self.assertEqual(
                (
                    await self.client.put(url, headers=self.headers, json=payload)
                ).status_code,
                422,
            )
        self.assertEqual(
            (await self.client.patch(url, headers=self.headers, json={})).status_code,
            422,
        )
        self.assertEqual((await self.client.get(url)).json(), card)
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={"manufactured_on": "2020-02-29", "expires_on": "2020-02-29"},
        )
        self.assertEqual(response.status_code, 200, response.text)

    async def test_current_tracking_and_expiration_rules_including_noop(self) -> None:
        """Сохранённая партия читается, но редактирование и no-op проверяют актуальный снимок."""
        for tracking in ("NONE", "LOT", "SERIAL", "LOT_AND_SERIAL"):
            for expiration in ("NONE", "OPTIONAL", "REQUIRED"):
                if tracking in ("NONE", "SERIAL") and expiration == "REQUIRED":
                    continue
                item = await self.create_item(f"{tracking}-{expiration}")
                card = await self.create_lot(item)
                response = await self.client.patch(
                    f"{self.items_url}/{item['id']}",
                    headers=self.headers,
                    json={"tracking_mode": tracking, "expiration_mode": expiration},
                )
                self.assertEqual(response.status_code, 200, response.text)
                response = await self.client.patch(
                    self.detail_url(card),
                    headers=self.headers,
                    json={"expires_on": None},
                )
                self.assertEqual(
                    response.status_code,
                    200 if tracking in ("LOT", "LOT_AND_SERIAL") else 422,
                    response.text,
                )
                response = await self.client.patch(
                    self.detail_url(card),
                    headers=self.headers,
                    json={"manufactured_on": "2020-01-01"},
                )
                self.assertEqual(
                    response.status_code,
                    200 if tracking in ("LOT", "LOT_AND_SERIAL") else 422,
                    response.text,
                )
                response = await self.client.patch(
                    self.detail_url(card),
                    headers=self.headers,
                    json={"expires_on": "2019-01-01", "manufactured_on": None},
                )
                allowed = tracking in ("LOT", "LOT_AND_SERIAL") and expiration != "NONE"
                self.assertEqual(
                    response.status_code, 200 if allowed else 422, response.text
                )

    async def test_missing_foreign_owner_and_tenant_are_404(self) -> None:
        """Запись не раскрывает и не перемещает партию другого SKU или tenant."""
        item = await self.create_item()
        other = await self.create_item("OTHER")
        card = await self.create_lot(item)
        for url in (
            f"{self.url(other)}/{card['id']}",
            f"{self.url(item)}/{uuid4()}",
            f"{self.items_url}/{uuid4()}/lots/{card['id']}",
        ):
            for method in ("PUT", "PATCH"):
                response = await self.client.request(
                    method,
                    url,
                    headers=self.headers,
                    json={"manufactured_on": None, "expires_on": None},
                )
                self.assertEqual(response.status_code, 404, response.text)
        self.app.state.test_context = replace(
            self.context,
            principal=Principal(str(uuid4()), str(self.other), "session", ("member",)),
        )
        try:
            self.assertEqual(
                (
                    await self.client.patch(
                        self.detail_url(card),
                        headers=self.headers,
                        json={"expires_on": None},
                    )
                ).status_code,
                404,
            )
        finally:
            self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.detail_url(card))).json(), card)

    async def race(
        self,
        identifier: str,
        first: Callable[[], Awaitable[Response]],
        second: Callable[[], Awaitable[Response]],
    ) -> tuple[Response, Response]:
        """Сериализует реальные HTTP-запросы на корне SKU без sleep и имитации SQL."""
        locked, resume, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original = SqlAlchemyInventoryItemRepository.get_for_update
        count = 0

        async def hold(
            repository: SqlAlchemyInventoryItemRepository, item_id: InventoryItemIdVO
        ) -> InventoryItem | None:
            """Удерживает первую фактическую блокировку до попытки второго процесса."""
            nonlocal count
            if item_id.uuid != UUID(identifier):
                return await original(repository, item_id)
            count += 1
            if count == 1:
                item = await original(repository, item_id)
                locked.set()
                await resume.wait()
                return item
            attempted.set()
            return await original(repository, item_id)

        async def invoke(operation: Callable[[], Awaitable[Response]]) -> Response:
            """Исполняет HTTP-операцию в собственной задаче и транзакции."""
            return await operation()

        tasks: list[asyncio.Task[Response]] = []
        with patch.object(SqlAlchemyInventoryItemRepository, "get_for_update", hold):
            try:
                tasks.append(asyncio.create_task(invoke(first)))
                await asyncio.wait_for(locked.wait(), 10)
                tasks.append(asyncio.create_task(invoke(second)))
                await asyncio.wait_for(attempted.wait(), 10)
                resume.set()
                responses = await asyncio.wait_for(asyncio.gather(*tasks), 15)
                return responses[0], responses[1]
            finally:
                resume.set()
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def test_concurrent_patch_merges_latest_and_put_replaces_dates(self) -> None:
        """Ожидающий PATCH не теряет пропущенную дату, PUT заменяет обе даты целиком."""
        for put_second in (False, True):
            item = await self.create_item(f"CONCURRENT-{put_second}")
            card = await self.create_lot(item)
            url = self.detail_url(card)
            first, second = await self.race(
                item["id"],
                lambda: self.client.patch(
                    url, headers=self.headers, json={"manufactured_on": "2021-01-01"}
                ),
                lambda: self.client.request(
                    "PUT" if put_second else "PATCH",
                    url,
                    headers=self.headers,
                    json=(
                        {"manufactured_on": None, "expires_on": "2031-01-01"}
                        if put_second
                        else {"expires_on": "2031-01-01"}
                    ),
                ),
            )
            self.assertEqual(
                (first.status_code, second.status_code),
                (200, 200),
                (first.text, second.text),
            )
            result = (await self.client.get(url)).json()
            self.assertEqual(
                result["manufactured_on"], None if put_second else "2021-01-01"
            )
            self.assertEqual(result["expires_on"], "2031-01-01")

    async def test_waiting_update_uses_new_item_settings(self) -> None:
        """После ожидания блокировки обновление видит отключённый партийный учёт."""
        item = await self.create_item()
        card = await self.create_lot(item)
        attempted = asyncio.Event()
        original = SqlAlchemyInventoryItemRepository.get_for_update

        async def read(
            repository: SqlAlchemyInventoryItemRepository, identifier: InventoryItemIdVO
        ) -> InventoryItem | None:
            """Отмечает попытку чтения до реального ожидающего SELECT."""
            attempted.set()
            return await original(repository, identifier)

        task: asyncio.Task[Response] | None = None
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                select(InventoryItemModel.id)
                .where(InventoryItemModel.id == UUID(item["id"]))
                .with_for_update()
            )
            with patch.object(
                SqlAlchemyInventoryItemRepository, "get_for_update", read
            ):
                try:
                    task = asyncio.create_task(
                        self.client.patch(
                            self.detail_url(card),
                            headers=self.headers,
                            json={"expires_on": None},
                        )
                    )
                    await asyncio.wait_for(attempted.wait(), 10)
                    await connection.execute(
                        update(InventoryItemModel)
                        .where(InventoryItemModel.id == UUID(item["id"]))
                        .values(tracking_mode="NONE")
                    )
                    await connection.commit()
                    response = await asyncio.wait_for(task, 10)
                    self.assertEqual(response.status_code, 422, response.text)
                finally:
                    if task is not None and not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((await self.client.get(self.detail_url(card))).json(), card)

    async def test_fresh_restore_save_only_dates_and_missing_returning(self) -> None:
        """Repository обновляет свежие даты, сохраняет идентичность и различает отсутствие без upsert."""
        item = await self.create_item()
        card = await self.create_lot(item)
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            sessions = async_sessionmaker(connection, expire_on_commit=False)
            async with sessions() as session:
                model = await session.get(StockLotModel, UUID(card["id"]))
                self.assertIsNotNone(model)
                await session.commit()
                async with self.engine.begin() as writer:
                    await bind_tenant_schema(writer, self.tenant.uuid, self.naming)
                    await writer.execute(
                        update(StockLotModel)
                        .where(StockLotModel.id == UUID(card["id"]))
                        .values(expires_on=date(2035, 1, 1))
                    )
                repository = SqlAlchemyStockLotRepository(session)
                lot = await repository.get_for_update(
                    StockLotIdVO(UUID(card["id"])),
                    inventory_item_id=InventoryItemIdVO(UUID(item["id"])),
                )
                self.assertIsNotNone(lot)
                assert lot is not None
                self.assertEqual(lot.dates.expires_on, date(2035, 1, 1))
                await session.rollback()
                missing = StockLot.restore(
                    identifier=StockLotIdVO(uuid4()),
                    inventory_item_id=lot.inventory_item_id,
                    number=LotNumberVO("unchanged"),
                    dates=StockDatesVO(),
                )
                with self.assertRaises(StockLotNotFoundError):
                    await repository.save(missing)
                await session.rollback()

    async def test_noop_does_not_write_and_write_commit_failures_roll_back(
        self,
    ) -> None:
        """No-op проходит Domain без UPDATE, ошибка после записи или commit не возвращает 200."""
        card = await self.create_lot(await self.create_item())
        url = self.detail_url(card)
        with patch.object(SqlAlchemyStockLotRepository, "save", autospec=True) as saved:
            response = await self.client.patch(
                url,
                headers=self.headers,
                json={"manufactured_on": card["manufactured_on"]},
            )
            self.assertEqual(response.status_code, 200, response.text)
            saved.assert_not_called()
        original = SqlAlchemyStockLotRepository.save

        async def fail(repository: SqlAlchemyStockLotRepository, lot: StockLot) -> None:
            """Прерывает процесс после фактического UPDATE до commit."""
            await original(repository, lot)
            raise RuntimeError("write failed")

        with patch.object(SqlAlchemyStockLotRepository, "save", fail):
            self.assertEqual(
                (
                    await self.client.patch(
                        url, headers=self.headers, json={"expires_on": None}
                    )
                ).status_code,
                500,
            )
        self.assertEqual((await self.client.get(url)).json(), card)

        def fail_commit(session: Session) -> None:
            """Срывает commit общей транзакции."""
            raise RuntimeError("commit failed")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                self.assertEqual(
                    (
                        await self.client.put(
                            url,
                            headers=self.headers,
                            json={"manufactured_on": None, "expires_on": None},
                        )
                    ).status_code,
                    500,
                )
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual((await self.client.get(url)).json(), card)

    async def test_auth_csrf_and_openapi_contracts(self) -> None:
        """Оба метода требуют auth/tenant/CSRF; PUT требует обе nullable-даты, PATCH допускает пропуски."""
        card = await self.create_lot(await self.create_item())
        for method in ("PUT", "PATCH"):
            for headers in (
                {},
                {**self.headers, "X-CSRF-Token": "bad"},
                {**self.headers, "Origin": "https://outside.example"},
            ):
                self.assertEqual(
                    (
                        await self.client.request(
                            method,
                            self.detail_url(card),
                            headers=headers,
                            json={"manufactured_on": None, "expires_on": None},
                        )
                    ).status_code,
                    403,
                )
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (
                await self.client.patch(
                    self.detail_url(card),
                    headers=self.headers,
                    json={"expires_on": None},
                )
            ).status_code,
            401,
        )
        self.app.state.test_context = replace(
            self.context,
            principal=Principal(str(uuid4()), None, "session", ("member",)),
        )
        self.assertEqual(
            (
                await self.client.patch(
                    self.detail_url(card),
                    headers=self.headers,
                    json={"expires_on": None},
                )
            ).status_code,
            403,
        )
        schemas = self.app.openapi()["components"]["schemas"]
        self.assertEqual(
            set(schemas["PutStockLotRequest"]["required"]),
            {"manufactured_on", "expires_on"},
        )
        self.assertNotIn("required", schemas["PatchStockLotRequest"])
        self.assertEqual(schemas["PutStockLotRequest"]["additionalProperties"], False)
