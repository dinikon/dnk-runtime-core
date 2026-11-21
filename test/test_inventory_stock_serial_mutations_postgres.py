"""PUT/PATCH Serial через реальные HTTP, блокировки и PostgreSQL."""

import asyncio
import os
import unittest
from dataclasses import replace
from unittest.mock import patch
from uuid import UUID, uuid4
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from test import test_inventory_stock_serial_postgres as fixture
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.repository import (
    SqlAlchemyStockSerialRepository,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockSerialMutationsPostgresTests(fixture.StockSerialPostgresTests):
    """Дополняет регрессию создания/чтения сценариями изменения номера и партии."""

    async def serial(
        self, item: dict[str, str], number: str = "000S-a", lot_id: str | None = None
    ) -> dict[str, str]:
        """Создаёт реальный экземпляр выбранного SKU для дальнейшего исправления."""
        response = await self.client.post(
            self.serial_url(item),
            headers=self.headers,
            json={"number": number, "lot_id": lot_id},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def lot(
        self, item: dict[str, str], number: str, expires: str | None = None
    ) -> dict[str, str]:
        """Создаёт партию с явно заданным календарным сроком."""
        response = await self.client.post(
            self.url(item),
            headers=self.headers,
            json={"number": number, "expires_on": expires},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_put_patch_preserve_ids_and_switch_date_source(self) -> None:
        """Смена партии обновляет проекции дат, номер сохраняет регистр и ведущие нули."""
        item = await self.create_item("LINKED", "LOT_AND_SERIAL", "REQUIRED")
        first, second = await self.lot(item, "000L-a", "2028-01-01"), await self.lot(
            item, "000L-b", None
        )
        serial = await self.serial(item, lot_id=first["id"])
        url = f"{self.serial_url(item)}/{serial['id']}"
        response = await self.client.put(
            url,
            headers=self.headers,
            json={"number": " 000S-A ", "lot_id": second["id"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual(
            (
                updated["id"],
                updated["inventory_item_id"],
                updated["number"],
                updated["lot_id"],
                updated["expires_on"],
            ),
            (serial["id"], item["id"], "000S-A", second["id"], None),
        )
        response = await self.client.patch(
            url, headers=self.headers, json={"number": "000S-b"}
        )
        self.assertEqual(
            (response.json()["number"], response.json()["lot_id"]),
            ("000S-b", second["id"]),
        )
        response = await self.client.patch(
            url, headers=self.headers, json={"lot_id": first["id"]}
        )
        self.assertEqual(
            (response.json()["number"], response.json()["expires_on"]),
            ("000S-b", "2028-01-01"),
        )
        self.assertEqual((await self.client.get(url)).json(), response.json())
        self.assertEqual(
            (await self.client.get(self.serial_url(item))).json()["items"][0],
            response.json(),
        )
        changed = await self.client.patch(
            f"{self.items_url}/{item['id']}",
            headers=self.headers,
            json={"tracking_mode": "SERIAL", "expiration_mode": "NONE"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(
            (
                await self.client.patch(
                    url, headers=self.headers, json={"number": "000S-c"}
                )
            ).status_code,
            422,
        )
        cleared = await self.client.patch(
            url, headers=self.headers, json={"lot_id": None}
        )
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(
            (
                cleared.json()["number"],
                cleared.json()["lot_id"],
                cleared.json()["date_source"],
                cleared.json()["expires_on"],
            ),
            ("000S-b", None, "NONE", None),
        )

    async def test_update_request_schema_and_current_rules_including_noop(self) -> None:
        """Форма PATCH/PUT проверяется Pydantic, актуальная совместимость — Domain даже для no-op."""
        item = await self.create_item("S", "SERIAL", "NONE")
        serial = await self.serial(item)
        url = f"{self.serial_url(item)}/{serial['id']}"
        for method, payload in (
            ("PATCH", {}),
            ("PUT", {}),
            ("PUT", {"number": "A"}),
            ("PUT", {"lot_id": None}),
            ("PATCH", {"number": None}),
            ("PATCH", {"number": 1}),
            ("PATCH", {"number": ""}),
            ("PATCH", {"lot_id": "bad"}),
            ("PATCH", {"number": "A", "expires_on": None}),
            ("PATCH", {"inventory_item_id": item["id"]}),
            ("PATCH", {"id": serial["id"]}),
        ):
            response = await self.client.request(
                method, url, headers=self.headers, json=payload
            )
            self.assertEqual(
                response.status_code, 422, (method, payload, response.text)
            )
        response = await self.client.patch(
            url, headers=self.headers, json={"number": " 000S-a "}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (await self.client.patch(url, json={"number": "A"})).status_code, 403
        )
        changed = await self.client.patch(
            f"{self.items_url}/{item['id']}",
            headers=self.headers,
            json={"tracking_mode": "NONE"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(
            (
                await self.client.patch(
                    url, headers=self.headers, json={"number": "000S-a"}
                )
            ).status_code,
            422,
        )
        self.assertEqual((await self.client.get(url)).status_code, 200)

    async def test_update_conflict_and_foreign_party_are_atomic(self) -> None:
        """UNIQUE и бизнес-ошибки не меняют ранее сохранённый номер и партию."""
        item = await self.create_item("A", "LOT_AND_SERIAL", "OPTIONAL")
        other = await self.create_item("B", "LOT_AND_SERIAL", "OPTIONAL")
        lot, foreign = await self.lot(item, "L"), await self.lot(other, "F")
        first = await self.serial(item, "000S", lot["id"])
        second = await self.serial(item, "000T", lot["id"])
        url = f"{self.serial_url(item)}/{second['id']}"
        for payload, status in (
            ({"number": first["number"]}, 409),
            ({"number": "changed", "lot_id": foreign["id"]}, 404),
            ({"lot_id": None}, 422),
        ):
            response = await self.client.patch(url, headers=self.headers, json=payload)
            self.assertEqual(response.status_code, status, response.text)
            self.assertEqual((await self.client.get(url)).json(), second)
        self.assertEqual(
            (
                await self.client.patch(
                    f"{self.serial_url(other)}/{second['id']}",
                    headers=self.headers,
                    json={"number": "X"},
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    f"{self.serial_url(item)}/{uuid4()}",
                    headers=self.headers,
                    json={"number": "X"},
                )
            ).status_code,
            404,
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual(
            (
                await self.client.patch(url, headers=self.headers, json={"number": "X"})
            ).status_code,
            404,
        )

    async def test_concurrent_partial_updates_keep_omitted_fields(self) -> None:
        """Ожидание блокировки перечитывает сохранённое состояние, не теряя другой PATCH."""
        item = await self.create_item("A", "LOT_AND_SERIAL", "OPTIONAL")
        first, second = await self.lot(item, "A"), await self.lot(item, "B")
        serial = await self.serial(item, lot_id=first["id"])
        url = f"{self.serial_url(item)}/{serial['id']}"
        results = await asyncio.gather(
            self.client.patch(url, headers=self.headers, json={"number": "000NEW"}),
            self.client.patch(url, headers=self.headers, json={"lot_id": second["id"]}),
        )
        self.assertEqual([r.status_code for r in results], [200, 200])
        current = (await self.client.get(url)).json()
        self.assertEqual(
            (current["number"], current["lot_id"]), ("000NEW", second["id"])
        )

    async def test_update_commit_failure_rolls_back(self) -> None:
        """Ошибка commit не превращается в 200 и откатывает выполненный UPDATE."""
        item = await self.create_item("S", "SERIAL", "NONE")
        serial = await self.serial(item)
        url = f"{self.serial_url(item)}/{serial['id']}"
        with patch.object(
            AsyncSession, "commit", side_effect=RuntimeError("commit failed")
        ):
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.client.patch(
                    url, headers=self.headers, json={"number": "changed"}
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual((await self.client.get(url)).json(), serial)

    async def test_locked_load_refreshes_cached_model(self) -> None:
        """FOR UPDATE с populate_existing не возвращает устаревшую ORM-модель."""
        item = await self.create_item("S", "SERIAL", "NONE")
        serial = await self.serial(item)
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with AsyncSession(connection, expire_on_commit=False) as session:
                cached = await session.get(StockSerialModel, UUID(serial["id"]))
                async with self.engine.begin() as external:
                    await bind_tenant_schema(external, self.tenant.uuid, self.naming)
                    await external.execute(
                        update(StockSerialModel)
                        .where(StockSerialModel.id == UUID(serial["id"]))
                        .values(number="fresh")
                    )
                restored = await SqlAlchemyStockSerialRepository(
                    session
                ).get_for_update(
                    StockSerialIdVO(UUID(serial["id"])),
                    inventory_item_id=InventoryItemIdVO(UUID(item["id"])),
                )
                self.assertEqual(restored.number.value, "fresh")
                self.assertEqual(cached.number, "fresh")
                await session.rollback()

    async def test_concurrent_rename_to_same_number_returns_one_conflict(self) -> None:
        """Два экземпляра одного SKU не могут получить одинаковый номер при конкурентном PATCH."""
        item = await self.create_item("S", "SERIAL", "NONE")
        first, second = await self.serial(item, "one"), await self.serial(item, "two")
        responses = await asyncio.gather(
            *(
                self.client.patch(
                    f"{self.serial_url(item)}/{serial['id']}",
                    headers=self.headers,
                    json={"number": "000shared"},
                )
                for serial in (first, second)
            )
        )
        self.assertEqual(
            sorted(response.status_code for response in responses), [200, 409]
        )
        page = (
            await self.client.get(self.serial_url(item), params={"search": "000shared"})
        ).json()
        self.assertEqual(page["total"], 1)
