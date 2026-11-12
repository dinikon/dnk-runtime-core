"""PUT/PATCH Warehouse на PostgreSQL с настоящими HTTP и UoW."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_warehouse_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class WarehouseMutationPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Повторно использует подготовку двух tenant из среза создания склада."""

    asyncSetUp = support.WarehousePostgresTests.asyncSetUp
    drop_schemas = support.WarehousePostgresTests.drop_schemas
    create = support.WarehousePostgresTests.create
    counts = support.WarehousePostgresTests.counts

    async def test_put_patch_activity_and_references_roundtrip(self) -> None:
        """Изменяет полное представление, редактирует неактивный склад и сохраняет локации."""
        created = (await self.create("original")).json()
        url = f"{self.url}/{created['id']}"
        payload = {"code": " RENAMED ", "name": " Новый склад ", "is_active": False}
        response = await self.client.put(url, headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(
            (body["code"], body["name"], body["is_active"]),
            ("renamed", "Новый склад", False),
        )
        self.assertEqual(body["id"], created["id"])
        self.assertEqual(
            body["default_storage_location_id"], created["default_storage_location_id"]
        )
        changed = await self.client.patch(
            url, headers=self.headers, json={"name": "Изменён заблокированный"}
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertFalse(changed.json()["is_active"])
        active = await self.client.patch(
            url, headers=self.headers, json={"is_active": True}
        )
        self.assertTrue(active.json()["is_active"])
        self.assertEqual((await self.client.get(url)).json(), active.json())
        filtered = (
            await self.client.get(
                self.url, params={"search": " RENAMED ", "is_active": True}
            )
        ).json()
        self.assertEqual(filtered["items"], [active.json()])
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                location = (await session.scalars(select(StockLocationModel))).one()
                self.assertEqual(
                    str(location.id), created["default_storage_location_id"]
                )
                self.assertTrue(location.is_active)
                self.assertEqual(location.code, "storage")
        self.assertEqual(await self.counts(), (1, 1))

    async def test_noop_does_not_update(self) -> None:
        """Повторный PUT и нормализованный PATCH не вызывают write-операцию."""
        created = (await self.create("original")).json()
        url = f"{self.url}/{created['id']}"
        with patch.object(
            SqlAlchemyWarehouseRepository,
            "save",
            side_effect=AssertionError("Unexpected UPDATE"),
        ):
            for method, payload in (
                (
                    "PUT",
                    {
                        "code": " ORIGINAL ",
                        "name": " Основной склад ",
                        "is_active": True,
                    },
                ),
                ("PATCH", {"code": "ORIGINAL"}),
                ("PATCH", {"is_active": True}),
            ):
                response = await self.client.request(
                    method, url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), created)

    async def test_validation_and_missing_records(self) -> None:
        """Различает пустой PATCH, null, строгий bool, неполный PUT и отсутствующий ID."""
        created = (await self.create("original")).json()
        url = f"{self.url}/{created['id']}"
        full = {"code": "valid", "name": "Name", "is_active": True}
        invalid = [
            {},
            {"default_storage_location_id": str(uuid4())},
            {"code": None},
            {"name": None},
            {"is_active": None},
            {"code": " "},
            {"name": "\u200bname"},
            {"code": 1},
            {"name": 1},
            {"is_active": 0},
            {"is_active": 1},
            {"is_active": "false"},
        ]
        for method in ("PATCH", "PUT"):
            for values in invalid:
                payload = values if method == "PATCH" else {**full, **values}
                if method == "PUT" and not values:
                    payload = {}
                with self.subTest(method=method, payload=payload):
                    response = await self.client.request(
                        method, url, headers=self.headers, json=payload
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        for field in full:
            incomplete = dict(full)
            del incomplete[field]
            self.assertEqual(
                (
                    await self.client.put(url, headers=self.headers, json=incomplete)
                ).status_code,
                422,
            )
        self.assertEqual((await self.client.get(url)).json(), created)
        for method, payload in (("PUT", full), ("PATCH", {"is_active": False})):
            self.assertEqual(
                (
                    await self.client.request(
                        method,
                        f"{self.url}/{uuid4()}",
                        headers=self.headers,
                        json=payload,
                    )
                ).status_code,
                404,
            )
            self.assertEqual(
                (
                    await self.client.request(
                        method,
                        f"{self.url}/invalid",
                        headers=self.headers,
                        json=payload,
                    )
                ).status_code,
                422,
            )
        self.assertEqual(await self.counts(), (1, 1))

    async def test_security_and_tenant_isolation(self) -> None:
        """Требует auth, tenant и CSRF; чужой UUID не позволяет изменить склад."""
        created = (await self.create("original")).json()
        url = f"{self.url}/{created['id']}"
        for method, payload in (
            ("PUT", {"code": "changed", "name": "Name", "is_active": False}),
            ("PATCH", {"is_active": False}),
        ):
            self.assertEqual(
                (await self.client.request(method, url, json=payload)).status_code, 403
            )
            for principal, expected in (
                (None, 401),
                (replace(self.context.principal, tenant_id=None), 403),
                (replace(self.context.principal, tenant_id=str(self.other)), 404),
            ):
                self.app.state.test_context = replace(self.context, principal=principal)
                response = await self.client.request(
                    method, url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, expected, response.text)
            self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(url)).json(), created)

    async def test_conflict_rolls_back_all_updated_fields(self) -> None:
        """Известный UNIQUE откатывает также название и активность обоих методов."""
        created = (await self.create("original")).json()
        self.assertEqual((await self.create("occupied")).status_code, 201)
        url = f"{self.url}/{created['id']}"
        for method in ("PUT", "PATCH"):
            response = await self.client.request(
                method,
                url,
                headers=self.headers,
                json={
                    "code": " OCCUPIED ",
                    "name": "Must rollback",
                    "is_active": False,
                },
            )
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual((await self.client.get(url)).json(), created)
        self.assertEqual(await self.counts(), (2, 2))

    async def test_commit_failure_rolls_back_update(self) -> None:
        """Ошибка commit не выдаёт 200 и сохраняет исходную карточку."""
        created = (await self.create("original")).json()
        url = f"{self.url}/{created['id']}"

        def fail_commit(session: Session) -> None:
            """Прерывает реальный commit внешнего UoW."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.client.patch(
                    url,
                    headers=self.headers,
                    json={"code": "rolled-back", "is_active": False},
                )
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(url)).json(), created)

    async def test_concurrent_independent_patches_preserve_both_changes(self) -> None:
        """Ожидающий PATCH загружает состояние после commit первого изменения."""
        created = (await self.create("original")).json()
        url = f"{self.url}/{created['id']}"
        locked, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyWarehouseRepository.get_for_update

        async def gated_get(
            repository: SqlAlchemyWarehouseRepository, identifier: WarehouseIdVO
        ) -> Warehouse | None:
            """Приостанавливает первую команду после фактического захвата блокировки."""
            result = await original(repository, identifier)
            if not locked.is_set():
                locked.set()
                await release.wait()
            return result

        with patch.object(SqlAlchemyWarehouseRepository, "get_for_update", gated_get):
            first = asyncio.create_task(
                self.client.patch(url, headers=self.headers, json={"code": "changed"})
            )
            await asyncio.wait_for(locked.wait(), 3)
            second = asyncio.create_task(
                self.client.patch(
                    url,
                    headers=self.headers,
                    json={"name": "Second Name", "is_active": False},
                )
            )
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(second.done())
            finally:
                release.set()
            responses = await asyncio.wait_for(asyncio.gather(first, second), 5)
        self.assertEqual(
            [r.status_code for r in responses], [200, 200], [r.text for r in responses]
        )
        result = (await self.client.get(url)).json()
        self.assertEqual(
            (result["code"], result["name"], result["is_active"]),
            ("changed", "Second Name", False),
        )
        self.assertEqual(
            result["default_storage_location_id"],
            created["default_storage_location_id"],
        )

    async def test_concurrent_same_code_has_one_winner(self) -> None:
        """UNIQUE сериализует смену разных кодов на один канонический код."""
        first, second = (await self.create("first")).json(), (
            await self.create("second")
        ).json()
        responses = await asyncio.gather(
            *(
                self.client.patch(
                    f"{self.url}/{row['id']}",
                    headers=self.headers,
                    json={"code": code, "name": "Winner", "is_active": False},
                )
                for row, code in ((first, " SHARED "), (second, "shared"))
            )
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 409],
            [r.text for r in responses],
        )
        for row, response in zip((first, second), responses):
            stored = (await self.client.get(f"{self.url}/{row['id']}")).json()
            self.assertEqual(
                stored, response.json() if response.status_code == 200 else row
            )

    async def test_locked_read_refreshes_cached_model_and_restores_reference(
        self,
    ) -> None:
        """Mapper восстанавливает полный агрегат после обновления из другого соединения."""
        created = (await self.create("original")).json()
        identifier = WarehouseIdVO(UUID(created["id"]))
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                cached = await session.get(WarehouseModel, identifier.uuid)
                self.assertIsNotNone(cached)
                changed = await self.client.patch(
                    f"{self.url}/{created['id']}",
                    headers=self.headers,
                    json={"code": "fresh", "name": "Fresh Name", "is_active": False},
                )
                self.assertEqual(changed.status_code, 200, changed.text)
                restored = await SqlAlchemyWarehouseRepository(session).get_for_update(
                    identifier
                )
                self.assertIsNotNone(restored)
                self.assertEqual(
                    (restored.code.value, restored.name.value, restored.is_active),
                    ("fresh", "Fresh Name", False),
                )
                self.assertEqual(
                    str(restored.default_storage_location_id),
                    created["default_storage_location_id"],
                )
