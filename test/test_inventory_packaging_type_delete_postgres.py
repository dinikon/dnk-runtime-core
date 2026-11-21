"""Удаление PackagingType на настоящем HTTP/UoW/PostgreSQL, включая гонки назначения."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, event, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.deletion_usage import (
    PackagingTypeDeletionUsage,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    get_packaging_type_usage,
)
from src.modules.inventory.presentation.packaging_type.router import router
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
class PackagingTypeDeletePostgresTests(unittest.IsolatedAsyncioTestCase):
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
        self.app.include_router(router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.types_url = "/api/console/inventory/packaging-types"
        self.items_url = "/api/console/inventory/items"

    async def drop_schemas(self) -> None:
        """Удаляет только две временные схемы текущего теста."""
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )

    async def create_type(self, code: str) -> Response:
        """Создаёт самостоятельный активный тип через публичный POST."""
        response = await self.client.post(
            self.types_url,
            headers=self.headers,
            json={"code": code, "name": f"Тара {code}"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response

    async def create_item(self, sku: str = "item") -> Response:
        """Создаёт SKU со штрихкодом для проверки сохранности независимого корня."""
        response = await self.client.post(
            self.items_url,
            headers=self.headers,
            json={"sku": sku, "barcodes": [f"000-{sku}"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response

    async def assign(
        self, item_id: str, type_id: str, code: str = "BOX-12"
    ) -> Response:
        """Назначает тип через InventoryItem, сохраняя штатный порядок блокировок."""
        return await self.client.post(
            f"{self.items_url}/{item_id}/packagings",
            headers=self.headers,
            json={
                "packaging_type_id": type_id,
                "code": code,
                "name": "Ящик",
                "content_quantity": "12",
                "content_uom": "PCS",
            },
        )

    async def remove(self, type_id: str) -> Response:
        """Удаляет тип в текущем tenant с настоящими auth и CSRF."""
        return await self.client.delete(
            f"{self.types_url}/{type_id}", headers=self.headers
        )

    async def race(
        self,
        type_id: str,
        first: Callable[[], Awaitable[Response]],
        second: Callable[[], Awaitable[Response]],
    ) -> tuple[Response, Response]:
        """Удерживает первую блокировку типа до попытки второго процесса без временных sleep."""
        locked, resume, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original = SqlAlchemyPackagingTypeRepository.get_for_update
        calls = 0

        async def hold(
            repository: SqlAlchemyPackagingTypeRepository, identifier: PackagingTypeIdVO
        ) -> PackagingType | None:
            """Первая операция удерживает блокировку, вторая выполняет реальный ожидающий SELECT."""
            nonlocal calls
            if identifier.uuid != UUID(type_id):
                return await original(repository, identifier)
            calls += 1
            if calls == 1:
                value = await original(repository, identifier)
                locked.set()
                await resume.wait()
                return value
            attempted.set()
            return await original(repository, identifier)

        async def invoke(operation: Callable[[], Awaitable[Response]]) -> Response:
            """Запускает HTTP-операцию в собственной задаче с отдельным соединением UoW."""
            return await operation()

        tasks: list[asyncio.Task[Response]] = []
        with patch.object(SqlAlchemyPackagingTypeRepository, "get_for_update", hold):
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

    async def test_unused_active_inactive_empty_response_repeat_and_reused_code(
        self,
    ) -> None:
        """Удаление разрешено в обоих состояниях, возвращает пустой 204 и освобождает точный код."""
        for active in (True, False):
            card = (await self.create_type("BOX")).json()
            if not active:
                response = await self.client.patch(
                    f"{self.types_url}/{card['id']}",
                    headers=self.headers,
                    json={"is_active": False},
                )
                self.assertEqual(response.status_code, 200, response.text)
            response = await self.remove(card["id"])
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(response.content, b"")
            self.assertNotIn("content-type", response.headers)
            self.assertEqual(
                (await self.client.get(f"{self.types_url}/{card['id']}")).status_code,
                404,
            )
            self.assertEqual((await self.remove(card["id"])).status_code, 404)
        self.assertEqual((await self.client.get(self.types_url)).json()["total"], 0)

    async def test_used_type_is_protected_and_can_be_deactivated(self) -> None:
        """Бизнес-проверка запрещает DELETE до репозитория и сохраняет все связанные данные."""
        kind = (await self.create_type("BOX")).json()
        item = (await self.create_item()).json()
        packaging = (await self.assign(item["id"], kind["id"])).json()
        original = SqlAlchemyPackagingTypeRepository.delete
        with patch.object(
            SqlAlchemyPackagingTypeRepository,
            "delete",
            autospec=True,
            side_effect=original,
        ) as delete_spy:
            for active in (True, False):
                response = await self.client.patch(
                    f"{self.types_url}/{kind['id']}",
                    headers=self.headers,
                    json={"is_active": active},
                )
                self.assertEqual(response.status_code, 200, response.text)
                response = await self.remove(kind["id"])
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn("деактивировать", response.json()["detail"])
            delete_spy.assert_not_called()
        self.assertEqual(
            (await self.client.get(f"{self.items_url}/{item['id']}")).json(), item
        )
        self.assertEqual(
            (await self.client.get(f"{self.items_url}/{item['id']}/packagings")).json()[
                "items"
            ],
            [packaging],
        )
        self.assertFalse(
            (await self.client.get(f"{self.types_url}/{kind['id']}")).json()[
                "is_active"
            ]
        )

    async def test_any_item_reference_is_enough_and_last_removal_frees_type(
        self,
    ) -> None:
        """Удаление одной ссылки не освобождает тип, пока остаётся упаковка другого товара."""
        kind = (await self.create_type("BOX")).json()
        for sku in ("one", "two"):
            item = (await self.create_item(sku)).json()
            response = await self.assign(item["id"], kind["id"])
            self.assertEqual(response.status_code, 201, response.text)
        listing = (await self.client.get(self.items_url)).json()["items"]
        for index, item in enumerate(listing):
            self.assertEqual((await self.remove(kind["id"])).status_code, 409)
            cards = (
                await self.client.get(f"{self.items_url}/{item['id']}/packagings")
            ).json()["items"]
            response = await self.client.delete(
                f"{self.items_url}/{item['id']}/packagings/{cards[0]['id']}",
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 204, response.text)
            if index == 0:
                self.assertEqual((await self.remove(kind["id"])).status_code, 409)
        self.assertEqual((await self.remove(kind["id"])).status_code, 204)
        self.assertEqual((await self.client.get(self.items_url)).json()["total"], 2)

    async def test_reassignment_allows_old_type_deletion_and_keeps_packaging(
        self,
    ) -> None:
        """Смена типа сохраняет упаковку и освобождает только прежний самостоятельный корень."""
        old = (await self.create_type("OLD")).json()
        new = (await self.create_type("NEW")).json()
        item = (await self.create_item()).json()
        card = (await self.assign(item["id"], old["id"])).json()
        url = f"{self.items_url}/{item['id']}/packagings/{card['id']}"
        response = await self.client.patch(
            url, headers=self.headers, json={"packaging_type_id": new["id"]}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.remove(old["id"])).status_code, 204)
        self.assertEqual(
            (await self.client.get(url)).json(),
            {**card, "packaging_type_id": new["id"]},
        )
        self.assertEqual((await self.remove(new["id"])).status_code, 409)

    async def test_existing_fk_protects_database_and_translates_defensive_conflict(
        self,
    ) -> None:
        """Реальный RESTRICT и его перевод защищают ссылки даже при неполном снимке использования."""
        kind = (await self.create_type("BOX")).json()
        item = (await self.create_item()).json()
        response = await self.assign(item["id"], kind["id"])
        self.assertEqual(response.status_code, 201, response.text)
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                await connection.execute(
                    delete(PackagingTypeModel).where(
                        PackagingTypeModel.id == UUID(kind["id"])
                    )
                )
        usage = Mock(get=AsyncMock(return_value=PackagingTypeDeletionUsage(False)))
        self.app.dependency_overrides[get_packaging_type_usage] = lambda: usage
        try:
            response = await self.remove(kind["id"])
            self.assertEqual(response.status_code, 409, response.text)
            usage.get.assert_awaited_once()
        finally:
            self.app.dependency_overrides.pop(get_packaging_type_usage)
        self.assertEqual(
            (await self.client.get(f"{self.types_url}/{kind['id']}")).json(), kind
        )
        self.assertEqual(
            (await self.client.get(f"{self.items_url}/{item['id']}/packagings")).json()[
                "total"
            ],
            1,
        )

    async def test_tenant_isolation_including_equal_ids_and_foreign_usage(self) -> None:
        """Ссылки одного tenant не запрещают удаление совпадающего UUID другого tenant."""
        kind = (await self.create_type("BOX")).json()
        item = (await self.create_item()).json()
        self.assertEqual((await self.assign(item["id"], kind["id"])).status_code, 201)
        self.app.state.test_context = replace(
            self.context,
            principal=Principal(str(uuid4()), str(self.other), "session", ("member",)),
        )
        try:
            self.assertEqual((await self.remove(kind["id"])).status_code, 404)
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.other.uuid, self.naming)
                await connection.execute(
                    insert(PackagingTypeModel).values(
                        id=UUID(kind["id"]),
                        code="BOX",
                        name="Other tenant",
                        is_active=False,
                    )
                )
            self.assertEqual((await self.remove(kind["id"])).status_code, 204)
        finally:
            self.app.state.test_context = self.context
        self.assertEqual(
            (await self.client.get(f"{self.types_url}/{kind['id']}")).json(), kind
        )
        self.assertEqual((await self.remove(kind["id"])).status_code, 409)

    async def test_delete_and_assignment_are_serialized_in_both_orders(self) -> None:
        """DELETE первым даёт назначению 404; назначение первым защищает тип ответом 409."""
        item = (await self.create_item()).json()
        for delete_first in (True, False):
            kind = (await self.create_type(f"BOX-{delete_first}")).json()
            remove = lambda: self.remove(kind["id"])
            assign = lambda: self.assign(
                item["id"], kind["id"], code=f"P-{delete_first}"
            )
            first, second = await self.race(
                kind["id"],
                remove if delete_first else assign,
                assign if delete_first else remove,
            )
            self.assertEqual(
                (first.status_code, second.status_code),
                (204, 404) if delete_first else (201, 409),
                (first.text, second.text),
            )
        cards = (
            await self.client.get(f"{self.items_url}/{item['id']}/packagings")
        ).json()["items"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["packaging_type_id"], kind["id"])

    async def test_delete_and_packaging_reassignment_are_serialized_in_both_orders(
        self,
    ) -> None:
        """Гонка смены типа не оставляет ссылку на удалённый тип и не теряет прежнюю упаковку."""
        original = (await self.create_type("ORIGINAL")).json()
        item = (await self.create_item()).json()
        for delete_first in (True, False):
            kind = (await self.create_type(f"NEW-{delete_first}")).json()
            card = (
                await self.assign(item["id"], original["id"], code=f"P-{delete_first}")
            ).json()
            url = f"{self.items_url}/{item['id']}/packagings/{card['id']}"
            remove = lambda: self.remove(kind["id"])
            change = lambda: self.client.patch(
                url, headers=self.headers, json={"packaging_type_id": kind["id"]}
            )
            first, second = await self.race(
                kind["id"],
                remove if delete_first else change,
                change if delete_first else remove,
            )
            self.assertEqual(
                (first.status_code, second.status_code),
                (204, 404) if delete_first else (200, 409),
                (first.text, second.text),
            )
            self.assertEqual(
                (await self.client.get(url)).json(),
                card if delete_first else {**card, "packaging_type_id": kind["id"]},
            )

    async def test_concurrent_repeat_delete_and_patch_never_resurrect_type(
        self,
    ) -> None:
        """Ожидающий DELETE получает 404, ожидающий PATCH не делает upsert удалённого типа."""
        for change in (False, True):
            kind = (await self.create_type(f"BOX-{change}")).json()
            remove = lambda: self.remove(kind["id"])
            second = (
                (
                    lambda: self.client.patch(
                        f"{self.types_url}/{kind['id']}",
                        headers=self.headers,
                        json={"name": "Late change"},
                    )
                )
                if change
                else remove
            )
            first_response, second_response = await self.race(
                kind["id"], remove, second
            )
            self.assertEqual(
                (first_response.status_code, second_response.status_code), (204, 404)
            )
            self.assertEqual(
                (await self.client.get(f"{self.types_url}/{kind['id']}")).status_code,
                404,
            )

    async def test_patch_before_delete_is_committed_then_type_is_removed(self) -> None:
        """Изменение первым может завершиться, последующее удаление не возвращает старую карточку."""
        kind = (await self.create_type("BOX")).json()
        first, second = await self.race(
            kind["id"],
            lambda: self.client.patch(
                f"{self.types_url}/{kind['id']}",
                headers=self.headers,
                json={"code": "CHANGED", "is_active": False},
            ),
            lambda: self.remove(kind["id"]),
        )
        self.assertEqual((first.status_code, second.status_code), (200, 204))
        self.assertEqual(
            (await self.client.get(f"{self.types_url}/{kind['id']}")).status_code, 404
        )

    async def test_write_and_commit_failures_roll_back_real_delete(self) -> None:
        """Уже выполненный SQL DELETE откатывается при отказе адаптера или commit, ответ не 204."""
        original = SqlAlchemyPackagingTypeRepository.delete

        async def fail_write(
            repository: SqlAlchemyPackagingTypeRepository, kind: PackagingType
        ) -> None:
            """Прерывает процесс после фактически выполненного DELETE до commit внешнего UoW."""
            await original(repository, kind)
            raise RuntimeError("write unavailable")

        kind = (await self.create_type("BOX")).json()
        with patch.object(SqlAlchemyPackagingTypeRepository, "delete", fail_write):
            response = await self.remove(kind["id"])
            self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(
            (await self.client.get(f"{self.types_url}/{kind['id']}")).json(), kind
        )

        def fail_commit(session: Session) -> None:
            """Срывает реальный commit общей транзакции после успешного handler."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.remove(kind["id"])
                self.assertEqual(response.status_code, 500, response.text)
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(
            (await self.client.get(f"{self.types_url}/{kind['id']}")).json(), kind
        )
