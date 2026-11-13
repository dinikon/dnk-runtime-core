"""Основная STORAGE: настоящий HTTP, tenant-UoW, FK и гонки PostgreSQL."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import Response
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)
from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_stock_location_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class DefaultStoragePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет реальный endpoint и блокировки на мигрированных схемах двух tenant."""

    drop_schemas = support.StockLocationPostgresTests.drop_schemas
    create = support.StockLocationPostgresTests.create
    counts = support.StockLocationPostgresTests.counts
    add_location = support.StockLocationPostgresTests.add_location

    async def asyncSetUp(self) -> None:
        """Создаёт склад с основной локацией и отдельную дочернюю STORAGE для назначения."""
        await support.StockLocationPostgresTests.asyncSetUp(self)
        response = await self.add_location(
            "replacement", parent_id=self.warehouse["default_storage_location_id"]
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.card = response.json()
        self.assignment_url = f"{self.warehouse_url}/default-storage-location"
        self.location_url = f"{self.locations_url}/{self.card['id']}"
        self.payload = {"location_id": self.card["id"]}

    async def assign(self) -> Response:
        """Назначает подготовленную STORAGE через публичный PUT и общий UoW."""
        return await self.client.put(
            self.assignment_url, headers=self.headers, json=self.payload
        )

    async def finish_task(self, task: asyncio.Task[Response]) -> None:
        """Отменяет незавершённый запрос до удаления тестовых tenant-схем."""
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    @asynccontextmanager
    async def hold_assignment(
        self,
    ) -> AsyncIterator[tuple[asyncio.Event, asyncio.Event]]:
        """Удерживает первый PUT после записи, сохраняя настоящие блокировки до commit."""
        ready, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyWarehouseRepository.save

        async def gated_save(
            repository: SqlAlchemyWarehouseRepository, warehouse: Warehouse
        ) -> None:
            """Сохраняет Warehouse и задерживает назначение выбранной локации до разрешения."""
            await original(repository, warehouse)
            if warehouse.id.uuid == UUID(
                self.warehouse["id"]
            ) and warehouse.default_storage_location_id == StockLocationIdVO(
                UUID(self.card["id"])
            ):
                ready.set()
                await release.wait()

        with patch.object(SqlAlchemyWarehouseRepository, "save", gated_save):
            try:
                yield ready, release
            finally:
                release.set()

    async def test_assignment_roundtrip_noop_and_old_location_release(self) -> None:
        """Меняет только основную ссылку, повтор не пишет, прежнюю локацию можно отключить."""
        response = await self.assign()
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**self.warehouse, "default_storage_location_id": self.card["id"]}
        self.assertEqual(response.json(), expected)
        self.assertEqual((await self.client.get(self.warehouse_url)).json(), expected)
        self.assertEqual((await self.client.get(self.url)).json()["items"], [expected])
        self.assertEqual((await self.client.get(self.location_url)).json(), self.card)
        previous_url = (
            f"{self.locations_url}/{self.warehouse['default_storage_location_id']}"
        )
        self.assertTrue((await self.client.get(previous_url)).json()["is_active"])
        with patch.object(
            SqlAlchemyWarehouseRepository,
            "save",
            side_effect=AssertionError("Unexpected UPDATE"),
        ):
            repeat = await self.assign()
        self.assertEqual(repeat.status_code, 200, repeat.text)
        self.assertEqual(repeat.json(), expected)
        old = await self.client.patch(
            previous_url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(old.status_code, 200, old.text)
        new = await self.client.patch(
            self.location_url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(new.status_code, 409, new.text)
        self.assertTrue((await self.client.get(self.location_url)).json()["is_active"])
        self.assertEqual(await self.counts(), (1, 2))

    async def test_inactive_warehouse_and_inactive_parent_allow_active_child(
        self,
    ) -> None:
        """Назначает активную дочернюю STORAGE без изменения активности склада и родителя."""
        parent = (await self.add_location("parent")).json()
        child = await self.add_location("child", parent_id=parent["id"])
        self.assertEqual(child.status_code, 201, child.text)
        for url in (f"{self.locations_url}/{parent['id']}", self.warehouse_url):
            response = await self.client.patch(
                url, headers=self.headers, json={"is_active": False}
            )
            self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.put(
            self.assignment_url,
            headers=self.headers,
            json={"location_id": child.json()["id"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_active"])
        self.assertEqual(
            response.json()["default_storage_location_id"], child.json()["id"]
        )
        self.assertFalse(
            (await self.client.get(f"{self.locations_url}/{parent['id']}")).json()[
                "is_active"
            ]
        )
        self.assertEqual(
            (
                await self.client.get(f"{self.locations_url}/{child.json()['id']}")
            ).json(),
            child.json(),
        )

    async def test_domain_rejections_preserve_previous_assignment(self) -> None:
        """Все остальные типы и неактивная STORAGE дают 422 без изменения основной ссылки."""
        for kind in ("RECEIVING", "SHIPPING", "QUARANTINE", "TRANSIT"):
            location = await self.add_location(kind.lower(), location_type=kind)
            self.assertEqual(location.status_code, 201, location.text)
            response = await self.client.put(
                self.assignment_url,
                headers=self.headers,
                json={"location_id": location.json()["id"]},
            )
            self.assertEqual(response.status_code, 422, response.text)
        deactivated = await self.client.patch(
            self.location_url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        response = await self.assign()
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_missing_foreign_and_other_tenant_ids_do_not_disclose_or_write(
        self,
    ) -> None:
        """Ограничивает обе ссылки текущим tenant и адрес выбранным складом."""
        other = (await self.create("other")).json()
        for url, location_id in (
            (f"{self.url}/{uuid4()}/default-storage-location", self.card["id"]),
            (self.assignment_url, str(uuid4())),
            (self.assignment_url, other["default_storage_location_id"]),
            (f"{self.url}/{other['id']}/default-storage-location", self.card["id"]),
        ):
            response = await self.client.put(
                url, headers=self.headers, json={"location_id": location_id}
            )
            self.assertEqual(response.status_code, 404, response.text)
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        try:
            response = await self.assign()
            self.assertEqual(response.status_code, 404, response.text)
        finally:
            self.app.state.test_context = self.context
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )
        self.assertEqual(await self.counts(), (2, 3))

    async def test_failure_after_update_rolls_back_assignment(self) -> None:
        """Исключение после реального UPDATE откатывает новую ссылку внешним UoW."""
        original = SqlAlchemyWarehouseRepository.save

        async def fail_after_save(
            repository: SqlAlchemyWarehouseRepository, warehouse: Warehouse
        ) -> None:
            """Прерывает процесс после отправленного SQL без локального rollback."""
            await original(repository, warehouse)
            raise RuntimeError("after update unavailable")

        with patch.object(SqlAlchemyWarehouseRepository, "save", fail_after_save):
            response = await self.assign()
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_commit_failure_never_returns_success(self) -> None:
        """Ошибка commit не выдаёт 200 и возвращает прежнюю основную ссылку."""

        def fail_commit(session: Session) -> None:
            """Прерывает commit общей транзакции после завершения handler."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.assign()
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_database_fk_protects_missing_and_foreign_locations(self) -> None:
        """Обход Domain всё равно отклоняется составным FK с переводом известной ошибки."""
        other = (await self.create("other")).json()
        for location_id in (uuid4(), UUID(other["default_storage_location_id"])):
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                async with self.sessions(bind=connection) as session:
                    repository = SqlAlchemyWarehouseRepository(session)
                    warehouse = await repository.get_for_update(
                        WarehouseIdVO(UUID(self.warehouse["id"]))
                    )
                    self.assertIsNotNone(warehouse)
                    if warehouse is None:
                        self.fail("Warehouse missing")
                    invalid = replace(
                        warehouse,
                        default_storage_location_id=StockLocationIdVO(location_id),
                    )
                    with self.assertRaises(StockLocationNotFoundError) as caught:
                        await repository.save(invalid)
                    self.assertIsInstance(caught.exception.__cause__, IntegrityError)
                    await session.rollback()
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_assignment_first_rejects_waiting_deactivation(self) -> None:
        """Назначение держит Warehouse, затем ожидающий PATCH видит новую основную и даёт 409."""
        async with self.hold_assignment() as (ready, release):
            first = asyncio.create_task(self.assign())
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(ready.wait(), 3)
                second = asyncio.create_task(
                    self.client.patch(
                        self.location_url,
                        headers=self.headers,
                        json={"is_active": False},
                    )
                )
                self.addAsyncCleanup(self.finish_task, second)
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(asyncio.shield(second), 0.1)
            finally:
                release.set()
            responses = await asyncio.wait_for(asyncio.gather(first, second), 5)
        self.assertEqual(
            [r.status_code for r in responses], [200, 409], [r.text for r in responses]
        )
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json()[
                "default_storage_location_id"
            ],
            self.card["id"],
        )
        self.assertTrue((await self.client.get(self.location_url)).json()["is_active"])

    async def test_deactivation_first_rejects_waiting_assignment(self) -> None:
        """Назначение ожидает FOR SHARE, перечитывает выключенную локацию и даёт 422."""
        ready, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyStockLocationRepository.save

        async def gated_save(
            repository: SqlAlchemyStockLocationRepository, location: StockLocation
        ) -> None:
            """Удерживает реальную деактивацию до начала конкурентного PUT."""
            await original(repository, location)
            ready.set()
            await release.wait()

        with patch.object(SqlAlchemyStockLocationRepository, "save", gated_save):
            first = asyncio.create_task(
                self.client.patch(
                    self.location_url, headers=self.headers, json={"is_active": False}
                )
            )
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(ready.wait(), 3)
                second = asyncio.create_task(self.assign())
                self.addAsyncCleanup(self.finish_task, second)
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(asyncio.shield(second), 0.1)
            finally:
                release.set()
            responses = await asyncio.wait_for(asyncio.gather(first, second), 5)
        self.assertEqual(
            [r.status_code for r in responses], [200, 422], [r.text for r in responses]
        )
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_concurrent_assignments_are_serialized(self) -> None:
        """Два PUT последовательно назначают разные локации без дедлока и потери настроек."""
        other = (await self.add_location("second")).json()
        async with self.hold_assignment() as (ready, release):
            first = asyncio.create_task(self.assign())
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(ready.wait(), 3)
                second = asyncio.create_task(
                    self.client.put(
                        self.assignment_url,
                        headers=self.headers,
                        json={"location_id": other["id"]},
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
            (await self.client.get(self.warehouse_url)).json(),
            {**self.warehouse, "default_storage_location_id": other["id"]},
        )

    async def test_warehouse_edit_preserves_waited_assignment(self) -> None:
        """Ожидающий PATCH перечитывает Warehouse и не возвращает прежнюю основную ссылку."""
        async with self.hold_assignment() as (ready, release):
            first = asyncio.create_task(self.assign())
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(ready.wait(), 3)
                second = asyncio.create_task(
                    self.client.patch(
                        self.warehouse_url,
                        headers=self.headers,
                        json={
                            "code": "renamed",
                            "name": "Новое имя",
                            "is_active": False,
                        },
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
            (await self.client.get(self.warehouse_url)).json(),
            {
                **self.warehouse,
                "code": "renamed",
                "name": "Новое имя",
                "is_active": False,
                "default_storage_location_id": self.card["id"],
            },
        )
