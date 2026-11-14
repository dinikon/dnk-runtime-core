"""StockSerial через настоящий HTTP, общий UoW, tenant-миграции и PostgreSQL."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from test import test_inventory_stock_lot_postgres as fixture
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.presentation.stock_serial.router import (
    router as serial_router,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockSerialPostgresTests(fixture.StockLotPostgresTests):
    """Дополняет регрессию партий проверками новых экземпляров и составного FK."""

    async def asyncSetUp(self) -> None:
        """Собирает три сценария Serial поверх реального приложения SKU и партий."""
        await super().asyncSetUp()
        self.app.include_router(serial_router, prefix="/api/console")

    def serial_url(self, item: dict[str, str]) -> str:
        """Возвращает адрес серийных экземпляров сохранённого SKU."""
        return f"{self.items_url}/{item['id']}/serials"

    async def test_serial_numbers_uniqueness_search_and_page(self) -> None:
        """Номер сохраняет регистр и нули; поиск буквальный, страницы и total согласованы."""
        item = await self.create_item("SERIAL", "SERIAL", "NONE")
        other = await self.create_item("OTHER", "SERIAL", "NONE")
        for number in ("000SN-a_%", "000SN-A_%", "000SN-b", "МойНомер"):
            response = await self.client.post(
                self.serial_url(item),
                headers=self.headers,
                json={"number": f" {number} "},
            )
            self.assertEqual(response.status_code, 201, response.text)
            card = response.json()
            self.assertEqual(card["number"], number)
            self.assertEqual(
                (
                    card["date_source"],
                    card["lot_id"],
                    card["manufactured_on"],
                    card["expires_on"],
                ),
                ("NONE", None, None, None),
            )
            self.assertEqual(
                (await self.client.get(f"{self.serial_url(item)}/{card['id']}")).json(),
                card,
            )
        response = await self.client.post(
            self.serial_url(item), headers=self.headers, json={"number": "000SN-a_%"}
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.post(
            self.serial_url(other), headers=self.headers, json={"number": "000SN-a_%"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        page = (
            await self.client.get(
                self.serial_url(item), params={"search": "_%", "limit": 1, "offset": 1}
            )
        ).json()
        self.assertEqual((page["total"], page["items"][0]["number"]), (2, "000SN-a_%"))
        self.assertEqual(
            (
                await self.client.get(self.serial_url(item), params={"search": "мой"})
            ).json()["total"],
            1,
        )

    async def test_linked_serial_uses_fresh_lot_dates_and_allows_incomplete_required(
        self,
    ) -> None:
        """Создание не требует готовности к поступлению, изменения Lot видны в обеих проекциях."""
        item = await self.create_item("LINKED", "LOT_AND_SERIAL", "REQUIRED")
        lot = (
            await self.client.post(
                self.url(item), headers=self.headers, json={"number": "000Lot-a"}
            )
        ).json()
        response = await self.client.post(
            self.serial_url(item),
            headers=self.headers,
            json={"number": "000S", "lot_id": lot["id"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        serial = response.json()
        self.assertEqual(
            (serial["date_source"], serial["lot_number"], serial["expires_on"]),
            ("LOT", "000Lot-a", None),
        )
        response = await self.client.patch(
            f"{self.url(item)}/{lot['id']}",
            headers=self.headers,
            json={"manufactured_on": "2024-02-29", "expires_on": "2028-12-31"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        for result in (
            (await self.client.get(f"{self.serial_url(item)}/{serial['id']}")).json(),
            (await self.client.get(self.serial_url(item))).json()["items"][0],
        ):
            self.assertEqual(
                (result["manufactured_on"], result["expires_on"]),
                ("2024-02-29", "2028-12-31"),
            )
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(InventoryItemModel)
                .where(InventoryItemModel.id == UUID(item["id"]))
                .values(tracking_mode="NONE", expiration_mode="NONE")
            )
        self.assertEqual(
            (
                await self.client.get(f"{self.serial_url(item)}/{serial['id']}")
            ).status_code,
            200,
        )
        self.assertEqual(
            (await self.client.get(self.serial_url(item))).json()["total"], 1
        )

    async def test_serial_missing_resources_modes_and_request_validation(self) -> None:
        """HTTP не принимает даты, чужие партии или несерийные режимы."""
        plain = await self.create_item("PLAIN", "SERIAL", "NONE")
        linked = await self.create_item("LINKED", "LOT_AND_SERIAL", "OPTIONAL")
        lot = (
            await self.client.post(
                self.url(linked), headers=self.headers, json={"number": "L"}
            )
        ).json()
        for payload in (
            {},
            {"number": 1},
            {"number": ""},
            {"number": "A\u200b"},
            {"number": "A", "manufactured_on": None},
            {"number": "A", "expires_on": "2028-01-01"},
            {"number": "A", "lot_id": "bad"},
        ):
            self.assertEqual(
                (
                    await self.client.post(
                        self.serial_url(plain), headers=self.headers, json=payload
                    )
                ).status_code,
                422,
                payload,
            )
        self.assertEqual(
            (
                await self.client.post(
                    self.serial_url(linked), headers=self.headers, json={"number": "A"}
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.serial_url(plain),
                    headers=self.headers,
                    json={"number": "A", "lot_id": lot["id"]},
                )
            ).status_code,
            404,
        )
        none = await self.create_item("NONE", "NONE", "NONE")
        self.assertEqual(
            (
                await self.client.post(
                    self.serial_url(none), headers=self.headers, json={"number": "A"}
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (await self.client.get(self.serial_url(plain))).json()["items"], []
        )
        self.assertEqual(
            (await self.client.get(f"{self.items_url}/{uuid4()}/serials")).status_code,
            404,
        )
        for params in (
            {"offset": -1},
            {"limit": 0},
            {"limit": 101},
            {"offset": 2147483648},
        ):
            self.assertEqual(
                (
                    await self.client.get(self.serial_url(plain), params=params)
                ).status_code,
                422,
            )
        self.assertEqual(
            (
                await self.client.post(self.serial_url(plain), json={"number": "A"})
            ).status_code,
            403,
        )

    async def test_serial_tenant_and_owner_isolation(self) -> None:
        """ID экземпляра не раскрывает данные другого SKU или tenant."""
        item = await self.create_item("S", "SERIAL", "NONE")
        other = await self.create_item("O", "SERIAL", "NONE")
        serial = (
            await self.client.post(
                self.serial_url(item), headers=self.headers, json={"number": "000A"}
            )
        ).json()
        self.assertEqual(
            (
                await self.client.get(f"{self.serial_url(other)}/{serial['id']}")
            ).status_code,
            404,
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual(
            (
                await self.client.get(f"{self.serial_url(item)}/{serial['id']}")
            ).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.get(self.serial_url(item))).status_code, 404
        )

    async def test_serial_deletion_business_guard_and_protective_fk(self) -> None:
        """Standalone Serial запрещает удаление SKU до DML и дополнительно защищён FK."""
        item = await self.create_item("S", "SERIAL", "NONE")
        await self.client.post(
            self.serial_url(item), headers=self.headers, json={"number": "S"}
        )
        response = await self.client.delete(
            f"{self.items_url}/{item['id']}", headers=self.headers
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("серийные", response.json()["detail"])
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    delete(InventoryItemModel).where(
                        InventoryItemModel.id == UUID(item["id"])
                    )
                )

    async def test_serial_composite_fk_and_lot_delete_protection(self) -> None:
        """БД отклоняет партию другого SKU и удаление связанной партии."""
        first = await self.create_item("ONE", "LOT_AND_SERIAL", "NONE")
        second = await self.create_item("TWO", "LOT_AND_SERIAL", "NONE")
        lot = (
            await self.client.post(
                self.url(first), headers=self.headers, json={"number": "L"}
            )
        ).json()
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    insert(StockSerialModel).values(
                        id=uuid4(),
                        inventory_item_id=UUID(second["id"]),
                        number="S",
                        lot_id=UUID(lot["id"]),
                    )
                )
        response = await self.client.post(
            self.serial_url(first),
            headers=self.headers,
            json={"number": "S", "lot_id": lot["id"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    delete(StockLotModel).where(StockLotModel.id == UUID(lot["id"]))
                )

    async def test_serial_concurrent_duplicate_creates_only_one(self) -> None:
        """Конкурентные POST сериализуются на SKU и завершаются 201/409 без дубля."""
        item = await self.create_item("S", "SERIAL", "NONE")
        responses = await asyncio.gather(
            *(
                self.client.post(
                    self.serial_url(item), headers=self.headers, json={"number": "000S"}
                )
                for _ in range(2)
            )
        )
        self.assertEqual(
            sorted(response.status_code for response in responses), [201, 409]
        )
        self.assertEqual(
            (await self.client.get(self.serial_url(item))).json()["total"], 1
        )

    async def test_serial_commit_failure_rolls_back_and_is_not_success(self) -> None:
        """Сбой общего commit не выдаёт 201 и откатывает уже выполненный INSERT экземпляра."""
        from sqlalchemy.ext.asyncio import AsyncSession

        item = await self.create_item("ROLLBACK", "SERIAL", "NONE")
        with patch.object(
            AsyncSession, "commit", side_effect=RuntimeError("test commit failed")
        ):
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.client.post(
                    self.serial_url(item), headers=self.headers, json={"number": "000S"}
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            (await self.client.get(self.serial_url(item))).json()["total"], 0
        )
