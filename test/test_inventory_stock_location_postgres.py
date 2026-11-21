"""StockLocation: настоящий HTTP, tenant-UoW, ограничения и конкурентные блокировки PostgreSQL."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import Response
from sqlalchemy import event, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)
from src.modules.inventory.infrastructure.stock_location.persistence.repository import (
    SqlAlchemyStockLocationRepository,
)
from src.modules.inventory.presentation.stock_location.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_warehouse_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockLocationPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Использует настоящие миграции и изолированные схемы двух tenant."""

    drop_schemas = support.WarehousePostgresTests.drop_schemas
    create = support.WarehousePostgresTests.create
    counts = support.WarehousePostgresTests.counts

    async def asyncSetUp(self) -> None:
        """Создаёт схемы, подключает маршруты и подготавливает склад с основной STORAGE."""
        await support.WarehousePostgresTests.asyncSetUp(self)
        self.app.include_router(router, prefix="/api/console")
        response = await self.create("main")
        self.assertEqual(response.status_code, 201, response.text)
        self.warehouse = response.json()
        self.warehouse_url = f"{self.url}/{self.warehouse['id']}"
        self.locations_url = f"{self.warehouse_url}/locations"

    async def add_location(
        self,
        code: str,
        *,
        name: str = "Location",
        location_type: str = "STORAGE",
        parent_id: str | None = None,
    ) -> Response:
        """Создаёт локацию через публичный POST и настоящий внешний UoW."""
        return await self.client.post(
            self.locations_url,
            headers=self.headers,
            json={
                "code": code,
                "name": name,
                "location_type": location_type,
                "parent_location_id": parent_id,
            },
        )

    async def set_active(self, identifier: str, value: bool) -> None:
        """Подготавливает локальную активность адреса для тестов Domain-проекции."""
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(StockLocationModel)
                .where(StockLocationModel.id == UUID(identifier))
                .values(is_active=value)
            )

    async def test_root_child_and_existing_default_roundtrip(self) -> None:
        """Читает автоматическую STORAGE, создаёт адреса и сохраняет основную ссылку."""
        initial = await self.client.get(self.locations_url)
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(
            initial.json()["items"][0]["id"],
            self.warehouse["default_storage_location_id"],
        )
        root = await self.add_location(" Straße-001 ", name=" Название ")
        self.assertEqual(root.status_code, 201, root.text)
        body = root.json()
        self.assertEqual(
            (body["code"], body["name"], body["parent_location_id"], body["is_active"]),
            ("strasse-001", "Название", None, True),
        )
        child = await self.add_location(
            "child", parent_id=body["id"], location_type="QUARANTINE"
        )
        self.assertEqual(child.status_code, 201, child.text)
        self.assertEqual(child.json()["parent_location_id"], body["id"])
        self.assertEqual(child.json()["location_type"], "QUARANTINE")
        self.assertEqual(
            (
                await self.client.get(f"{self.locations_url}/{child.json()['id']}")
            ).json(),
            child.json(),
        )
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )
        self.assertEqual(await self.counts(), (1, 3))

    async def test_filters_pagination_and_literal_search_share_total(self) -> None:
        """Применяет поиск, тип, parent и false одинаково к total и странице."""
        parent = self.warehouse["default_storage_location_id"]
        for code, name, kind in [
            ("b", "КИЇВ", "STORAGE"),
            ("a", "Київ", "STORAGE"),
            ("literal%_", "Literal", "RECEIVING"),
            ("other", "Other", "SHIPPING"),
        ]:
            response = await self.add_location(
                code, name=name, location_type=kind, parent_id=parent
            )
            self.assertEqual(response.status_code, 201, response.text)
            if code == "b":
                inactive = response.json()["id"]
                await self.set_active(inactive, False)
        response = await self.client.get(
            self.locations_url,
            params={
                "parent_location_id": parent,
                "location_type": "STORAGE",
                "is_active": "false",
                "search": " київ ",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([row["id"] for row in response.json()["items"]], [inactive])
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(
            (await self.client.get(self.locations_url, params={"search": "%_"})).json()[
                "total"
            ],
            1,
        )
        self.assertEqual(
            (
                await self.client.get(
                    self.locations_url, params={"search": "literal%_"}
                )
            ).json()["items"][0]["code"],
            "literal%_",
        )
        page = (
            await self.client.get(
                self.locations_url,
                params={"parent_location_id": parent, "offset": 1, "limit": 2},
            )
        ).json()
        self.assertEqual((page["total"], page["offset"], page["limit"]), (4, 1, 2))
        self.assertEqual([row["code"] for row in page["items"]], ["b", "literal%_"])
        empty = (
            await self.client.get(
                self.locations_url, params={"offset": 100, "limit": 2}
            )
        ).json()
        self.assertEqual((empty["items"], empty["total"]), ([], 5))
        self.assertEqual(
            (
                await self.client.get(
                    self.locations_url, params={"parent_location_id": str(uuid4())}
                )
            ).json()["total"],
            0,
        )
        self.assertEqual(
            (
                await self.client.get(self.locations_url, params={"search": "missing"})
            ).json()["total"],
            0,
        )

    async def test_empty_existing_warehouse_and_missing_are_distinct(self) -> None:
        """Пустая карточка без основной ссылки даёт пустую страницу; отсутствующая — 404."""
        empty_id = uuid4()
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                insert(WarehouseModel).values(
                    id=empty_id,
                    code="empty",
                    name="Empty",
                    is_active=True,
                    default_storage_location_id=None,
                )
            )
        response = await self.client.get(f"{self.url}/{empty_id}/locations")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(), {"items": [], "total": 0, "offset": 0, "limit": 50}
        )
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}/locations")).status_code, 404
        )

    async def test_warehouse_and_tenant_boundaries(self) -> None:
        """Запрещает чужого родителя, чужую карточку и доступ по UUID другого tenant."""
        second = (await self.create("second")).json()
        foreign_parent = second["default_storage_location_id"]
        response = await self.add_location("child", parent_id=foreign_parent)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            (
                await self.client.get(f"{self.locations_url}/{foreign_parent}")
            ).status_code,
            404,
        )
        missing = await self.add_location("child", parent_id=str(uuid4()))
        self.assertEqual(missing.status_code, 404, missing.text)
        first = await self.add_location("same")
        response = await self.client.post(
            f"{self.url}/{second['id']}/locations",
            headers=self.headers,
            json={"code": "same", "name": "Same", "location_type": "STORAGE"},
        )
        self.assertEqual((first.status_code, response.status_code), (201, 201))
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        for path in (
            self.locations_url,
            f"{self.locations_url}/{self.warehouse['default_storage_location_id']}",
        ):
            self.assertEqual((await self.client.get(path)).status_code, 404)
        self.assertEqual((await self.add_location("hidden")).status_code, 404)
        self.app.state.test_context = self.context
        self.assertEqual(await self.counts(), (2, 4))

    async def test_inactive_parent_allowed_and_inactive_warehouse_rejected(
        self,
    ) -> None:
        """Активность родителя не наследуется; активность склада требуется только для создания."""
        parent = (await self.add_location("parent")).json()
        await self.set_active(parent["id"], False)
        child = await self.add_location("child", parent_id=parent["id"])
        self.assertEqual(child.status_code, 201, child.text)
        self.assertTrue(child.json()["is_active"])
        response = await self.client.patch(
            self.warehouse_url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.add_location("blocked")).status_code, 422)
        self.assertEqual((await self.client.get(self.locations_url)).json()["total"], 3)
        self.assertEqual(
            (
                await self.client.get(f"{self.locations_url}/{child.json()['id']}")
            ).status_code,
            200,
        )
        self.assertEqual(await self.counts(), (1, 3))

    async def test_same_canonical_code_race_has_one_winner(self) -> None:
        """Одновременные INSERT делят совместимую блокировку склада, UNIQUE выбирает победителя."""
        responses = await asyncio.wait_for(
            asyncio.gather(self.add_location(" SAME "), self.add_location("same")), 5
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        self.assertEqual(await self.counts(), (1, 2))
        response = await self.add_location(" STORAGE ")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_failed_commit_rolls_back_new_location(self) -> None:
        """Ошибка commit не оставляет INSERT и не выдаёт успешный ответ."""

        def fail_commit(session: Session) -> None:
            """Прерывает реальный commit после выполнения handler."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.add_location("retry")
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.counts(), (1, 1))
        self.assertEqual((await self.add_location("retry")).status_code, 201)
        self.assertEqual(
            (await self.client.get(self.warehouse_url)).json(), self.warehouse
        )

    async def test_parallel_creations_share_lock_and_delay_deactivation(self) -> None:
        """Второй POST проходит при незавершённом первом, деактивация ожидает оба."""
        locked, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyWarehouseRepository.get_for_share

        async def gated_read(
            repository: SqlAlchemyWarehouseRepository, identifier: WarehouseIdVO
        ) -> Warehouse | None:
            """Удерживает только первую блокировку FOR SHARE до разрешения теста."""
            result = await original(repository, identifier)
            if not locked.is_set():
                locked.set()
                await release.wait()
            return result

        first = None
        try:
            with patch.object(
                SqlAlchemyWarehouseRepository, "get_for_share", gated_read
            ):
                first = asyncio.create_task(self.add_location("first"))
                await asyncio.wait_for(locked.wait(), 3)
                second = await asyncio.wait_for(self.add_location("second"), 3)
                self.assertEqual(second.status_code, 201, second.text)
                deactivate = asyncio.create_task(
                    self.client.patch(
                        self.warehouse_url,
                        headers=self.headers,
                        json={"is_active": False},
                    )
                )
                try:
                    with self.assertRaises(asyncio.TimeoutError):
                        await asyncio.wait_for(asyncio.shield(deactivate), 0.1)
                finally:
                    release.set()
                results = await asyncio.wait_for(asyncio.gather(first, deactivate), 5)
        finally:
            release.set()
            if first is not None and not first.done():
                await asyncio.wait_for(first, 5)
        self.assertEqual(
            [r.status_code for r in results], [201, 200], [r.text for r in results]
        )
        self.assertEqual((await self.add_location("late")).status_code, 422)
        self.assertEqual(await self.counts(), (1, 3))

    async def test_creation_waits_for_deactivation_and_reads_new_state(self) -> None:
        """Ожидающий FOR SHARE после commit деактивации получает false и отклоняет POST."""
        locked, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyWarehouseRepository.get_for_update

        async def gated_update(
            repository: SqlAlchemyWarehouseRepository, identifier: WarehouseIdVO
        ) -> Warehouse | None:
            """Удерживает реальную блокировку UPDATE до начала второго HTTP-запроса."""
            result = await original(repository, identifier)
            locked.set()
            await release.wait()
            return result

        deactivate = None
        try:
            with patch.object(
                SqlAlchemyWarehouseRepository, "get_for_update", gated_update
            ):
                deactivate = asyncio.create_task(
                    self.client.patch(
                        self.warehouse_url,
                        headers=self.headers,
                        json={"is_active": False},
                    )
                )
                await asyncio.wait_for(locked.wait(), 3)
                creation = asyncio.create_task(self.add_location("blocked"))
                try:
                    with self.assertRaises(asyncio.TimeoutError):
                        await asyncio.wait_for(asyncio.shield(creation), 0.1)
                finally:
                    release.set()
                results = await asyncio.wait_for(
                    asyncio.gather(deactivate, creation), 5
                )
        finally:
            release.set()
            if deactivate is not None and not deactivate.done():
                await asyncio.wait_for(deactivate, 5)
        self.assertEqual(
            [r.status_code for r in results], [200, 422], [r.text for r in results]
        )
        self.assertEqual(await self.counts(), (1, 1))

    async def test_repositories_refresh_identity_map_and_restore_nullable_fields(
        self,
    ) -> None:
        """Новое чтение не подменяется ранее загруженными ORM-экземплярами."""
        location_id = StockLocationIdVO(
            UUID(self.warehouse["default_storage_location_id"])
        )
        warehouse_id = WarehouseIdVO(UUID(self.warehouse["id"]))
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                warehouse_model = await session.get(WarehouseModel, warehouse_id.uuid)
                location_model = await session.get(StockLocationModel, location_id.uuid)
                self.assertTrue(warehouse_model.is_active)
                self.assertTrue(location_model.is_active)
                await self.set_active(str(location_id), False)
                await self.client.patch(
                    self.warehouse_url, headers=self.headers, json={"is_active": False}
                )
                location = await SqlAlchemyStockLocationRepository(session).get(
                    location_id
                )
                warehouse = await SqlAlchemyWarehouseRepository(session).get_for_share(
                    warehouse_id
                )
                self.assertIsNotNone(location)
                self.assertIsNotNone(warehouse)
                self.assertFalse(location.is_active)
                self.assertFalse(warehouse.is_active)
                self.assertIsNone(location.parent_location_id)
                self.assertEqual(warehouse.default_storage_location_id, location.id)

    async def test_real_fk_translation_and_unknown_constraint(self) -> None:
        """Защитные FK переводятся по именам, конфликт первичного ключа остаётся техническим."""
        for warehouse_id, parent_id, identifier, expected in (
            (uuid4(), None, uuid4(), WarehouseNotFoundError),
            (UUID(self.warehouse["id"]), uuid4(), uuid4(), StockLocationNotFoundError),
            (
                UUID(self.warehouse["id"]),
                None,
                UUID(self.warehouse["default_storage_location_id"]),
                IntegrityError,
            ),
        ):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                async with self.sessions(bind=connection) as session:
                    location = StockLocation.restore(
                        identifier=StockLocationIdVO(identifier),
                        warehouse_id=WarehouseIdVO(warehouse_id),
                        parent_location_id=(
                            StockLocationIdVO(parent_id) if parent_id else None
                        ),
                        code=LocationCodeVO("unique-code"),
                        name=LocationNameVO("Name"),
                        location_type=LocationType.STORAGE,
                        is_active=True,
                    )
                    with self.subTest(expected=expected), self.assertRaises(expected):
                        async with session.begin_nested():
                            await SqlAlchemyStockLocationRepository(session).add(
                                location
                            )
        self.assertEqual(await self.counts(), (1, 1))
