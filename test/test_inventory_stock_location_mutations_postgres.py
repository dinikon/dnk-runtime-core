"""PUT/PATCH локаций на PostgreSQL: транзакции, конкурентность и защита основной STORAGE."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import Response
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import Session

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import StockLocationInactiveError
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)
from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_stock_location_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockLocationMutationsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Использует настоящий HTTP, общую сессию UoW и миграции двух tenant."""

    drop_schemas = support.StockLocationPostgresTests.drop_schemas
    create = support.StockLocationPostgresTests.create
    counts = support.StockLocationPostgresTests.counts
    add_location = support.StockLocationPostgresTests.add_location

    async def asyncSetUp(self) -> None:
        """Создаёт склад, основную STORAGE и отдельную изменяемую дочернюю STORAGE."""
        await support.StockLocationPostgresTests.asyncSetUp(self)
        response = await self.add_location(
            "original",
            name="Original",
            parent_id=self.warehouse["default_storage_location_id"],
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.card = response.json()
        self.location_url = f"{self.locations_url}/{self.card['id']}"
        self.full = {"code": "original", "name": "Original", "is_active": True}

    async def assign_default(
        self, ready: asyncio.Event | None = None, release: asyncio.Event | None = None
    ) -> None:
        """Моделирует будущий сценарий назначения через Domain и порты одного внешнего UoW."""
        warehouse_id = WarehouseIdVO(UUID(self.warehouse["id"]))
        location_id = StockLocationIdVO(UUID(self.card["id"]))
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                warehouses = SqlAlchemyWarehouseRepository(uow.session)
                locations = SqlAlchemyStockLocationRepository(uow.session)
                warehouse = await warehouses.get_for_update(warehouse_id)
                location = await locations.get_for_update(
                    location_id, warehouse_id=warehouse_id
                )
                assert warehouse is not None and location is not None
                await warehouses.save(
                    warehouse.set_default_storage_location(location.snapshot())
                )
                if ready is not None:
                    ready.set()
                if release is not None:
                    await release.wait()

    async def finish_task(
        self, task: asyncio.Task[Response] | asyncio.Task[None]
    ) -> None:
        """Отменяет незавершённую задачу до удаления схем при отказе конкурентного теста."""
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_put_patch_roundtrip_preserves_fixed_fields_and_filters(self) -> None:
        """Изменяет три поля, сохраняет принадлежность/родителя/тип и актуализирует список."""
        response = await self.client.put(
            self.location_url,
            headers=self.headers,
            json={"code": " RENAMED ", "name": " New Name ", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        changed = {
            **self.card,
            "code": "renamed",
            "name": "New Name",
            "is_active": False,
        }
        self.assertEqual(response.json(), changed)
        self.assertEqual((await self.client.get(self.location_url)).json(), changed)
        response = await self.client.patch(
            self.location_url, headers=self.headers, json={"name": "Changed inactive"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {**changed, "name": "Changed inactive"})
        listed = (
            await self.client.get(
                self.locations_url, params={"search": "renamed", "is_active": "false"}
            )
        ).json()
        self.assertEqual(listed["items"], [response.json()])
        self.assertEqual(listed["total"], 1)
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_noop_never_calls_save(self) -> None:
        """Нормализованный PUT и повторная деактивация не вызывают SQL UPDATE."""
        with patch.object(
            SqlAlchemyStockLocationRepository,
            "save",
            side_effect=AssertionError("Unexpected UPDATE"),
        ):
            for method, payload in [
                (
                    "PUT",
                    {"code": " ORIGINAL ", "name": " Original ", "is_active": True},
                ),
                ("PATCH", {"is_active": True}),
                ("PATCH", {"name": "Original"}),
            ]:
                response = await self.client.request(
                    method, self.location_url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), self.card)
        response = await self.client.patch(
            self.location_url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        with patch.object(
            SqlAlchemyStockLocationRepository,
            "save",
            side_effect=AssertionError("Unexpected UPDATE"),
        ):
            repeated = await self.client.patch(
                self.location_url, headers=self.headers, json={"is_active": False}
            )
            self.assertEqual(repeated.status_code, 200, repeated.text)

    async def test_main_storage_can_be_renamed_but_not_deactivated_atomically(
        self,
    ) -> None:
        """Основная ссылка защищена Domain, отказ не сохраняет другие поля того же запроса."""
        url = f"{self.locations_url}/{self.warehouse['default_storage_location_id']}"
        renamed = await self.client.patch(
            url,
            headers=self.headers,
            json={"code": "main-storage", "name": "Main storage"},
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)
        for active in (True, False):
            await self.client.patch(
                self.warehouse_url, headers=self.headers, json={"is_active": active}
            )
            for method in ("PUT", "PATCH"):
                response = await self.client.request(
                    method,
                    url,
                    headers=self.headers,
                    json={
                        "code": "must-rollback",
                        "name": "Must rollback",
                        "is_active": False,
                    },
                )
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual((await self.client.get(url)).json(), renamed.json())
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json()[
                "default_storage_location_id"
            ],
            self.warehouse["default_storage_location_id"],
        )

    async def test_inactive_warehouse_allows_local_settings_without_cascade(
        self,
    ) -> None:
        """Локальная активность не активирует склад и не меняет детей или родителя."""
        child = await self.add_location("child", parent_id=self.card["id"])
        self.assertEqual(child.status_code, 201, child.text)
        await self.client.patch(
            self.warehouse_url, headers=self.headers, json={"is_active": False}
        )
        response = await self.client.put(
            self.location_url,
            headers=self.headers,
            json={"code": "blocked", "name": "Blocked", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(
            (
                await self.client.get(f"{self.locations_url}/{child.json()['id']}")
            ).json()["is_active"]
        )
        response = await self.client.patch(
            self.location_url, headers=self.headers, json={"is_active": True}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["is_active"])
        self.assertFalse(
            (await self.client.get(self.warehouse_url)).json()["is_active"]
        )

    async def test_missing_wrong_warehouse_and_tenant_are_404_without_upsert(
        self,
    ) -> None:
        """Идентификаторы обоих корней ограничивают запись, UUID другого tenant скрыт."""
        other = (await self.create("other")).json()
        paths = [
            f"{self.url}/{uuid4()}/locations/{self.card['id']}",
            f"{self.locations_url}/{uuid4()}",
            f"{self.url}/{other['id']}/locations/{self.card['id']}",
        ]
        for method in ("PUT", "PATCH"):
            for path in paths:
                response = await self.client.request(
                    method, path, headers=self.headers, json=self.full
                )
                self.assertEqual(response.status_code, 404, response.text)
            self.app.state.test_context = replace(
                self.context,
                principal=replace(self.context.principal, tenant_id=str(self.other)),
            )
            response = await self.client.request(
                method, self.location_url, headers=self.headers, json=self.full
            )
            self.assertEqual(response.status_code, 404, response.text)
            self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.location_url)).json(), self.card)
        self.assertEqual(await self.counts(), (2, 3))

    async def test_unique_conflict_rolls_back_every_changed_field(self) -> None:
        """Канонический UNIQUE откатывает также название и активность; другой склад независим."""
        occupied = await self.add_location("occupied")
        self.assertEqual(occupied.status_code, 201, occupied.text)
        for method in ("PUT", "PATCH"):
            response = await self.client.request(
                method,
                self.location_url,
                headers=self.headers,
                json={
                    "code": " OCCUPIED ",
                    "name": "Must rollback",
                    "is_active": False,
                },
            )
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(
                (await self.client.get(self.location_url)).json(), self.card
            )
        other = (await self.create("other")).json()
        response = await self.client.put(
            f"{self.url}/{other['id']}/locations/{other['default_storage_location_id']}",
            headers=self.headers,
            json=self.full,
        )
        self.assertEqual(response.status_code, 200, response.text)

    async def test_commit_failure_never_returns_success_or_partial_update(self) -> None:
        """Ошибка commit откатывает все поля существующей карточки."""

        def fail_commit(session: Session) -> None:
            """Прерывает реальный commit внешнего UoW."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.client.put(
                    self.location_url,
                    headers=self.headers,
                    json={"code": "rollback", "name": "Rollback", "is_active": False},
                )
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(self.location_url)).json(), self.card)

    async def test_same_canonical_code_race_has_single_winner(self) -> None:
        """Два адреса одного склада не получают один код; проигравшая карточка сохранена."""
        other = (await self.add_location("other")).json()
        urls = [self.location_url, f"{self.locations_url}/{other['id']}"]
        responses = await asyncio.wait_for(
            asyncio.gather(
                *(
                    self.client.patch(
                        url,
                        headers=self.headers,
                        json={"code": " SHARED ", "name": "Winner", "is_active": False},
                    )
                    for url in urls
                )
            ),
            5,
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 409],
            [r.text for r in responses],
        )
        for url, original, response in zip(urls, [self.card, other], responses):
            self.assertEqual(
                (await self.client.get(url)).json(),
                response.json() if response.status_code == 200 else original,
            )

    async def test_waiting_patch_reads_latest_state_and_preserves_other_fields(
        self,
    ) -> None:
        """Две команды одного адреса сериализуются и сохраняют изменения разных полей."""
        locked, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyStockLocationRepository.get_for_update

        async def gated_read(
            repository: SqlAlchemyStockLocationRepository,
            identifier: StockLocationIdVO,
            *,
            warehouse_id: WarehouseIdVO,
        ) -> StockLocation | None:
            """Останавливает первую команду после фактического захвата блокировки адреса."""
            result = await original(repository, identifier, warehouse_id=warehouse_id)
            if not locked.is_set():
                locked.set()
                await release.wait()
            return result

        with patch.object(
            SqlAlchemyStockLocationRepository, "get_for_update", gated_read
        ):
            first = asyncio.create_task(
                self.client.patch(
                    self.location_url, headers=self.headers, json={"code": "changed"}
                )
            )
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(locked.wait(), 3)
                second = asyncio.create_task(
                    self.client.patch(
                        self.location_url,
                        headers=self.headers,
                        json={"name": "Second", "is_active": False},
                    )
                )
                self.addAsyncCleanup(self.finish_task, second)
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(asyncio.shield(second), 0.1)
            finally:
                release.set()
            responses = await asyncio.wait_for(asyncio.gather(first, second), 5)
        self.assertEqual(
            [r.status_code for r in responses], [200, 200], [r.text for r in responses]
        )
        self.assertEqual(
            (await self.client.get(self.location_url)).json(),
            {**self.card, "code": "changed", "name": "Second", "is_active": False},
        )

    async def test_different_locations_can_update_concurrently(self) -> None:
        """FOR SHARE склада позволяет второму адресу завершиться, пока первый заблокирован."""
        other = (await self.add_location("other")).json()
        locked, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyStockLocationRepository.get_for_update

        async def gated_read(
            repository: SqlAlchemyStockLocationRepository,
            identifier: StockLocationIdVO,
            *,
            warehouse_id: WarehouseIdVO,
        ) -> StockLocation | None:
            """Удерживает только выбранный адрес, не сериализуя весь склад."""
            result = await original(repository, identifier, warehouse_id=warehouse_id)
            if str(identifier) == self.card["id"]:
                locked.set()
                await release.wait()
            return result

        with patch.object(
            SqlAlchemyStockLocationRepository, "get_for_update", gated_read
        ):
            first = asyncio.create_task(
                self.client.patch(
                    self.location_url, headers=self.headers, json={"name": "First"}
                )
            )
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(locked.wait(), 3)
                second = await asyncio.wait_for(
                    self.client.patch(
                        f"{self.locations_url}/{other['id']}",
                        headers=self.headers,
                        json={"name": "Second"},
                    ),
                    3,
                )
                self.assertEqual(second.status_code, 200, second.text)
            finally:
                release.set()
            self.assertEqual((await asyncio.wait_for(first, 5)).status_code, 200)

    async def test_assignment_first_prevents_waiting_deactivation(self) -> None:
        """После конкурентного назначения FOR SHARE читает новую основную ссылку и даёт 409."""
        ready, release = asyncio.Event(), asyncio.Event()
        assignment = asyncio.create_task(self.assign_default(ready, release))
        self.addAsyncCleanup(self.finish_task, assignment)
        try:
            await asyncio.wait_for(ready.wait(), 3)
            deactivation = asyncio.create_task(
                self.client.patch(
                    self.location_url, headers=self.headers, json={"is_active": False}
                )
            )
            self.addAsyncCleanup(self.finish_task, deactivation)
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(deactivation), 0.1)
        finally:
            release.set()
        await asyncio.wait_for(assignment, 5)
        response = await asyncio.wait_for(deactivation, 5)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertTrue((await self.client.get(self.location_url)).json()["is_active"])
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json()[
                "default_storage_location_id"
            ],
            self.card["id"],
        )

    async def test_deactivation_first_prevents_assignment_of_inactive_location(
        self,
    ) -> None:
        """Назначение ожидает редактирование и Domain отклоняет уже неактивную STORAGE."""
        ready, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyStockLocationRepository.get_for_update

        async def gated_read(
            repository: SqlAlchemyStockLocationRepository,
            identifier: StockLocationIdVO,
            *,
            warehouse_id: WarehouseIdVO,
        ) -> StockLocation | None:
            """Останавливает первую команду после блокировки склада и адреса."""
            result = await original(repository, identifier, warehouse_id=warehouse_id)
            if not ready.is_set():
                ready.set()
                await release.wait()
            return result

        with patch.object(
            SqlAlchemyStockLocationRepository, "get_for_update", gated_read
        ):
            deactivation = asyncio.create_task(
                self.client.patch(
                    self.location_url, headers=self.headers, json={"is_active": False}
                )
            )
            self.addAsyncCleanup(self.finish_task, deactivation)
            try:
                await asyncio.wait_for(ready.wait(), 3)
                assignment = asyncio.create_task(self.assign_default())
                self.addAsyncCleanup(self.finish_task, assignment)
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(asyncio.shield(assignment), 0.1)
            finally:
                release.set()
            response = await asyncio.wait_for(deactivation, 5)
            self.assertEqual(response.status_code, 200, response.text)
            with self.assertRaises(StockLocationInactiveError):
                await asyncio.wait_for(assignment, 5)
        self.assertFalse((await self.client.get(self.location_url)).json()["is_active"])
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json()[
                "default_storage_location_id"
            ],
            self.warehouse["default_storage_location_id"],
        )

    async def test_locked_read_refreshes_identity_map_and_is_scoped_to_warehouse(
        self,
    ) -> None:
        """Старая ORM-карточка не подменяет актуальное состояние заблокированного адреса."""
        warehouse_id = WarehouseIdVO(UUID(self.warehouse["id"]))
        location_id = StockLocationIdVO(UUID(self.card["id"]))
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                cached = await session.get(StockLocationModel, location_id.uuid)
                assert cached is not None
                self.assertEqual(cached.code, "original")
                response = await self.client.patch(
                    self.location_url,
                    headers=self.headers,
                    json={"code": "fresh", "is_active": False},
                )
                self.assertEqual(response.status_code, 200, response.text)
                await SqlAlchemyWarehouseRepository(session).get_for_share(warehouse_id)
                repository = SqlAlchemyStockLocationRepository(session)
                restored = await repository.get_for_update(
                    location_id, warehouse_id=warehouse_id
                )
                assert restored is not None
                self.assertEqual(
                    (restored.code.value, restored.is_active), ("fresh", False)
                )
                self.assertEqual(
                    str(restored.parent_location_id), self.card["parent_location_id"]
                )
                self.assertIsNone(
                    await repository.get_for_update(
                        location_id, warehouse_id=WarehouseIdVO(uuid4())
                    )
                )
