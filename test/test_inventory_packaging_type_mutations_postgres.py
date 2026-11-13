"""PUT/PATCH типов тары на PostgreSQL: блокировки, точные коды и атомарность."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import Response
from sqlalchemy import event
from sqlalchemy.orm import Session

from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_packaging_type_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class PackagingTypeMutationsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Использует реальный HTTP, Domain, адаптеры и общий UoW двух tenant."""

    drop_schemas = support.PackagingTypePostgresTests.drop_schemas
    create = support.PackagingTypePostgresTests.create
    count = support.PackagingTypePostgresTests.count

    async def asyncSetUp(self) -> None:
        """Создаёт независимый тип тары и URL его редактирования."""
        await support.PackagingTypePostgresTests.asyncSetUp(self)
        response = await self.create("BOX", "Ящик")
        self.assertEqual(response.status_code, 201, response.text)
        self.card = response.json()
        self.detail_url = f"{self.url}/{self.card['id']}"
        self.full = {"code": "BOX", "name": "Ящик", "is_active": True}

    async def finish_task(self, task: asyncio.Task[Response]) -> None:
        """Отменяет незавершённые запросы до удаления тестовых tenant-схем."""
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_put_patch_roundtrip_preserves_id_and_updates_filters(self) -> None:
        """Меняет три значения, редактирует неактивный тип и сохраняет UUID."""
        response = await self.client.put(
            self.detail_url,
            headers=self.headers,
            json={"code": " RENAMED ", "name": " Новое имя ", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        changed = {
            **self.card,
            "code": "RENAMED",
            "name": "Новое имя",
            "is_active": False,
        }
        self.assertEqual(response.json(), changed)
        self.assertEqual((await self.client.get(self.detail_url)).json(), changed)
        response = await self.client.patch(
            self.detail_url, headers=self.headers, json={"name": "Изменён неактивный"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_active"])
        filtered = (
            await self.client.get(
                self.url, params={"search": "renamed", "is_active": "false"}
            )
        ).json()
        self.assertEqual(filtered["items"], [response.json()])
        self.assertEqual(filtered["total"], 1)
        active = await self.client.patch(
            self.detail_url, headers=self.headers, json={"is_active": True}
        )
        self.assertEqual(active.status_code, 200, active.text)
        self.assertTrue(active.json()["is_active"])
        self.assertEqual(active.json()["id"], self.card["id"])
        self.assertEqual(await self.count(), 1)

    async def test_noop_and_repeated_activity_do_not_write(self) -> None:
        """Trim-эквивалентный PUT и PATCH без изменения активности не вызывают save."""
        with patch.object(
            SqlAlchemyPackagingTypeRepository,
            "save",
            side_effect=AssertionError("Unexpected UPDATE"),
        ):
            for method, payload in (
                ("PUT", {"code": " BOX ", "name": " Ящик ", "is_active": True}),
                ("PATCH", {"code": "BOX"}),
                ("PATCH", {"is_active": True}),
            ):
                response = await self.client.request(
                    method, self.detail_url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), self.card)
        response = await self.client.patch(
            self.detail_url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        with patch.object(
            SqlAlchemyPackagingTypeRepository,
            "save",
            side_effect=AssertionError("Unexpected UPDATE"),
        ):
            repeated = await self.client.patch(
                self.detail_url, headers=self.headers, json={"is_active": False}
            )
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertFalse(repeated.json()["is_active"])

    async def test_code_case_is_preserved_and_uniqueness_remains_exact(self) -> None:
        """Смена BOX в box реальна; занятый BOX затем даёт конфликт, а не casefold."""
        changed = await self.client.patch(
            self.detail_url, headers=self.headers, json={"code": "box"}
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["code"], "box")
        other = await self.create("BOX")
        self.assertEqual(other.status_code, 201, other.text)
        conflict = await self.client.put(
            self.detail_url,
            headers=self.headers,
            json={"code": " BOX ", "name": "Must rollback", "is_active": False},
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(
            (await self.client.get(self.detail_url)).json(), changed.json()
        )
        self.assertEqual(await self.count(), 2)

    async def test_invalid_domain_values_and_missing_id_do_not_write_or_upsert(
        self,
    ) -> None:
        """Невалидное имя не сохраняет подготовленные код/активность; чужой ID не создаётся."""
        for method in ("PUT", "PATCH"):
            response = await self.client.request(
                method,
                self.detail_url,
                headers=self.headers,
                json={"code": "NEW", "name": "Bad\u200bName", "is_active": False},
            )
            self.assertEqual(response.status_code, 422, response.text)
            response = await self.client.request(
                method, f"{self.url}/{uuid4()}", headers=self.headers, json=self.full
            )
            self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)
        self.assertEqual(await self.count(), 1)

    async def test_auth_csrf_and_tenant_boundaries(self) -> None:
        """Оба метода требуют auth/tenant/CSRF и не меняют запись по чужому UUID."""
        for method in ("PUT", "PATCH"):
            self.assertEqual(
                (
                    await self.client.request(method, self.detail_url, json=self.full)
                ).status_code,
                403,
            )
            for principal, expected in (
                (None, 401),
                (replace(self.context.principal, tenant_id=None), 403),
                (replace(self.context.principal, tenant_id=str(self.other)), 404),
            ):
                self.app.state.test_context = replace(self.context, principal=principal)
                try:
                    response = await self.client.request(
                        method, self.detail_url, headers=self.headers, json=self.full
                    )
                    self.assertEqual(response.status_code, expected, response.text)
                finally:
                    self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)

    async def test_unique_conflict_rolls_back_every_field(self) -> None:
        """Занятый точный код не позволяет частично сохранить имя или активность."""
        other = await self.create("TAKEN")
        self.assertEqual(other.status_code, 201, other.text)
        for method in ("PUT", "PATCH"):
            response = await self.client.request(
                method,
                self.detail_url,
                headers=self.headers,
                json={"code": " TAKEN ", "name": "Must rollback", "is_active": False},
            )
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{other.json()['id']}")).json(),
            other.json(),
        )

    async def test_commit_failure_does_not_return_200_and_rolls_back(self) -> None:
        """Отказ commit после handler не оставляет обновлённую карточку."""

        def fail_commit(session: Session) -> None:
            """Прерывает реальный commit внешнего tenant-UoW."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.client.patch(
                    self.detail_url,
                    headers=self.headers,
                    json={"code": "NEW", "name": "New", "is_active": False},
                )
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)

    async def test_failure_after_update_rolls_back(self) -> None:
        """Исключение после реального UPDATE откатывает всю транзакцию."""
        original = SqlAlchemyPackagingTypeRepository.save

        async def fail_after_save(
            repository: SqlAlchemyPackagingTypeRepository, packaging_type: PackagingType
        ) -> None:
            """Прерывает запрос после отправленного SQL без локального rollback."""
            await original(repository, packaging_type)
            raise RuntimeError("after update unavailable")

        with patch.object(SqlAlchemyPackagingTypeRepository, "save", fail_after_save):
            response = await self.client.put(
                self.detail_url,
                headers=self.headers,
                json={"code": "NEW", "name": "New", "is_active": False},
            )
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(self.detail_url)).json(), self.card)

    async def test_concurrent_independent_patches_preserve_both_changes(self) -> None:
        """Ожидающий PATCH перечитывает корень после commit и сохраняет чужое поле."""
        ready, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyPackagingTypeRepository.get_for_update

        async def gated_get(
            repository: SqlAlchemyPackagingTypeRepository, identifier: PackagingTypeIdVO
        ) -> PackagingType | None:
            """Удерживает только первый запрос после фактической блокировки корня."""
            result = await original(repository, identifier)
            if not ready.is_set():
                ready.set()
                await release.wait()
            return result

        with patch.object(
            SqlAlchemyPackagingTypeRepository, "get_for_update", gated_get
        ):
            first = asyncio.create_task(
                self.client.patch(
                    self.detail_url, headers=self.headers, json={"code": "NEW"}
                )
            )
            self.addAsyncCleanup(self.finish_task, first)
            try:
                await asyncio.wait_for(ready.wait(), 3)
                second = asyncio.create_task(
                    self.client.patch(
                        self.detail_url,
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
            (await self.client.get(self.detail_url)).json(),
            {**self.card, "code": "NEW", "name": "Second", "is_active": False},
        )

    async def test_concurrent_same_code_has_one_winner_without_partial_update(
        self,
    ) -> None:
        """UNIQUE допускает только один UPDATE разных корней на одинаковый точный код."""
        other = (await self.create("OTHER")).json()
        responses = await asyncio.wait_for(
            asyncio.gather(
                *(
                    self.client.patch(
                        f"{self.url}/{card['id']}",
                        headers=self.headers,
                        json={"code": code, "name": "Winner", "is_active": False},
                    )
                    for card, code in ((self.card, " SHARED "), (other, "SHARED"))
                )
            ),
            5,
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 409],
            [r.text for r in responses],
        )
        for before, response in zip((self.card, other), responses):
            self.assertEqual(
                (await self.client.get(f"{self.url}/{before['id']}")).json(),
                response.json() if response.status_code == 200 else before,
            )
        self.assertEqual(await self.count(), 2)

    async def test_locked_read_replaces_cached_model_and_restores_full_domain(
        self,
    ) -> None:
        """Write repository восстанавливает свежее состояние поверх старой ORM-модели."""
        identifier = PackagingTypeIdVO(UUID(self.card["id"]))
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                cached = await session.get(PackagingTypeModel, identifier.uuid)
                self.assertIsNotNone(cached)
                changed = await self.client.patch(
                    self.detail_url,
                    headers=self.headers,
                    json={"code": "FRESH", "name": "Fresh", "is_active": False},
                )
                self.assertEqual(changed.status_code, 200, changed.text)
                restored = await SqlAlchemyPackagingTypeRepository(
                    session
                ).get_for_update(identifier)
                self.assertIsNotNone(restored)
                if restored is None:
                    self.fail("PackagingType missing")
                self.assertEqual(
                    (
                        restored.id,
                        restored.code.value,
                        restored.name.value,
                        restored.is_active,
                    ),
                    (identifier, "FRESH", "Fresh", False),
                )

    async def test_save_missing_record_never_inserts(self) -> None:
        """UPDATE отсутствующего агрегата с RETURNING даёт ошибку без скрытого upsert."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                repository = SqlAlchemyPackagingTypeRepository(session)
                kind = await repository.get_for_update(
                    PackagingTypeIdVO(UUID(self.card["id"]))
                )
                self.assertIsNotNone(kind)
                if kind is None:
                    self.fail("PackagingType missing")
                missing = replace(kind, id=PackagingTypeIdVO(uuid4()))
                self.assertIsNone(await repository.get_for_update(missing.id))
                with self.assertRaises(PackagingTypeNotFoundError):
                    await repository.save(missing)
        self.assertEqual(await self.count(), 1)
