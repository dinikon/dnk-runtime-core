"""Типы тары: настоящий HTTP, tenant-UoW, миграции, UNIQUE и конкурентность PostgreSQL."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import Response
from sqlalchemy import event, func, insert, inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.infrastructure.persistence.models.packaging_type import (
    PackagingTypeModel,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.repository import (
    SqlAlchemyPackagingTypeRepository,
)
from src.modules.inventory.infrastructure.packaging_type.persistence.query_repository import (
    SqlAlchemyPackagingTypeQueryRepository,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.query import (
    GetPackagingTypeQuery,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.presentation.packaging_type.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from test import test_inventory_warehouse_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class PackagingTypePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет полный путь API и отдельную таблицу двух мигрированных tenant."""

    drop_schemas = support.WarehousePostgresTests.drop_schemas

    async def asyncSetUp(self) -> None:
        """Подготавливает два tenant и реальный router без подмены handlers или UoW."""
        await support.WarehousePostgresTests.asyncSetUp(self)
        self.app.include_router(router, prefix="/api/console")
        self.url = "/api/console/inventory/packaging-types"

    async def create(self, code: str, name: str = "Ящик") -> Response:
        """Создаёт тип тары через публичный POST с настоящей CSRF-защитой."""
        return await self.client.post(
            self.url, headers=self.headers, json={"code": code, "name": name}
        )

    async def count(self) -> int:
        """Считает записи своего tenant после завершения внешнего HTTP-UoW."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                return (
                    await session.execute(
                        select(func.count()).select_from(PackagingTypeModel)
                    )
                ).scalar_one()

    async def test_create_list_get_roundtrip_and_exact_case_uniqueness(self) -> None:
        """Сохраняет регистр и defaults, отличает BOX от box, trim-дубликат даёт 409."""
        created = await self.create(" BOX ", " Ящик ")
        self.assertEqual(created.status_code, 201, created.text)
        card = created.json()
        self.assertEqual(set(card), {"id", "code", "name", "is_active"})
        UUID(card["id"])
        self.assertEqual(
            (card["code"], card["name"], card["is_active"]), ("BOX", "Ящик", True)
        )
        self.assertEqual(
            (await self.client.get(f"{self.url}/{card['id']}")).json(), card
        )
        listed = await self.client.get(self.url)
        self.assertEqual(
            listed.json(), {"items": [card], "total": 1, "offset": 0, "limit": 50}
        )
        lower = await self.create("box")
        self.assertEqual(lower.status_code, 201, lower.text)
        self.assertNotEqual(card["id"], lower.json()["id"])
        duplicate = await self.create(" BOX ", "Другой")
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(await self.count(), 2)
        self.assertEqual(
            (await self.client.get(self.url, params={"search": "bOx"})).json()["total"],
            2,
        )

    async def test_filters_unicode_literal_search_and_total_share_conditions(
        self,
    ) -> None:
        """Регистр поиска не влияет на точную уникальность и не превращает %/_ в шаблон."""
        cards = []
        for code, name in (
            ("BOX", "ЯЩИК"),
            ("box", "Ящик"),
            ("КОДКИЇВ", "Unicode code"),
            ("literal%_\\tail", "Literal"),
            ("z", "Other"),
        ):
            response = await self.create(code, name)
            self.assertEqual(response.status_code, 201, response.text)
            cards.append(response.json())
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(PackagingTypeModel)
                .where(PackagingTypeModel.id == UUID(cards[1]["id"]))
                .values(is_active=False)
            )
        filtered = await self.client.get(
            self.url, params={"search": " ящик ", "is_active": "false", "limit": 1}
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual(
            filtered.json(),
            {
                "items": [{**cards[1], "is_active": False}],
                "total": 1,
                "offset": 0,
                "limit": 1,
            },
        )
        for search, expected in (("кодкиїв", cards[2]), ("%_\\", cards[3])):
            result = (await self.client.get(self.url, params={"search": search})).json()
            self.assertEqual(result["items"], [expected])
            self.assertEqual(result["total"], 1)
        page = (
            await self.client.get(self.url, params={"offset": 1, "limit": 2})
        ).json()
        expected = sorted(
            [
                {**c, "is_active": False} if c["id"] == cards[1]["id"] else c
                for c in cards
            ],
            key=lambda c: (c["code"], c["id"]),
        )
        self.assertEqual(
            page, {"items": expected[1:3], "total": 5, "offset": 1, "limit": 2}
        )
        empty = (
            await self.client.get(
                self.url, params={"offset": 100, "is_active": "false"}
            )
        ).json()
        self.assertEqual(empty, {"items": [], "total": 1, "offset": 100, "limit": 50})
        self.assertEqual(
            (await self.client.get(self.url, params={"search": "missing"})).json()[
                "total"
            ],
            0,
        )

    async def test_tenant_isolation_and_missing_ids(self) -> None:
        """Одинаковый код допустим в другом tenant, чужая карточка не раскрывается."""
        own = (await self.create("BOX")).json()
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        try:
            self.assertEqual((await self.client.get(self.url)).json()["total"], 0)
            self.assertEqual(
                (await self.client.get(f"{self.url}/{own['id']}")).status_code, 404
            )
            other = await self.create("BOX")
            self.assertEqual(other.status_code, 201, other.text)
            self.assertEqual(
                (await self.client.get(self.url)).json()["items"], [other.json()]
            )
        finally:
            self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.url)).json()["items"], [own])
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}")).status_code, 404
        )
        self.assertEqual(await self.count(), 1)

    async def test_concurrent_duplicate_creates_have_one_winner(self) -> None:
        """Атомарный UNIQUE разрешает только один INSERT одинакового кода."""
        responses = await asyncio.wait_for(
            asyncio.gather(self.create(" SAME "), self.create("SAME")), 5
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        winner = next(r.json() for r in responses if r.status_code == 201)
        self.assertEqual((await self.client.get(self.url)).json()["items"], [winner])
        self.assertEqual(await self.count(), 1)

    async def test_failure_after_insert_rolls_back(self) -> None:
        """Ошибка после реального INSERT откатывает запись, не выдавая успешный 201."""
        original = SqlAlchemyPackagingTypeRepository.add

        async def fail_after_insert(
            repository: SqlAlchemyPackagingTypeRepository, packaging_type: PackagingType
        ) -> None:
            """Прерывает сценарий после SQL, оставляя rollback внешнему UoW."""
            await original(repository, packaging_type)
            raise RuntimeError("after insert unavailable")

        with patch.object(SqlAlchemyPackagingTypeRepository, "add", fail_after_insert):
            response = await self.create("BOX")
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.count(), 0)

    async def test_commit_failure_rolls_back_and_never_returns_201(self) -> None:
        """Проверяет завершение общего UoW до отправки успешного ответа."""

        def fail_commit(session: Session) -> None:
            """Прерывает реальный commit после успешного возврата handler."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.create("BOX")
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.count(), 0)

    async def test_query_refreshes_existing_identity_map_without_domain_restore(
        self,
    ) -> None:
        """Обязательное перечитывание возвращает новое состояние поверх ORM identity map."""
        card = (await self.create("BOX")).json()
        identifier = UUID(card["id"])
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                model = await session.get(PackagingTypeModel, identifier)
                self.assertIsNotNone(model)
                async with self.engine.begin() as other:
                    await bind_tenant_schema(other, self.tenant.uuid, self.naming)
                    await other.execute(
                        update(PackagingTypeModel)
                        .where(PackagingTypeModel.id == identifier)
                        .values(name="Updated", is_active=False)
                    )
                result = await SqlAlchemyPackagingTypeQueryRepository(
                    session
                ).get_details(GetPackagingTypeQuery(PackagingTypeIdVO(identifier)))
                self.assertIsNotNone(result)
                if result is None:
                    self.fail("Projection missing")
                self.assertEqual((result.name, result.is_active), ("Updated", False))
                self.assertIsNotNone(model)

    async def test_migration_metadata_constraints_and_upgrade_existing_tenant(
        self,
    ) -> None:
        """Новая ревизия совпадает с metadata и не меняет предыдущие таблицы при откате."""
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)

            def unique_constraints(
                conn: Connection,
            ) -> dict[str | None, tuple[str, ...]]:
                """Читает именованные UNIQUE текущей тестовой схемы."""
                return {
                    constraint["name"]: tuple(constraint["column_names"])
                    for constraint in inspect(conn).get_unique_constraints(
                        "packaging_types", schema=self.schemas[0]
                    )
                }

            def table_names(conn: Connection) -> list[str]:
                """Читает таблицы после upgrade или downgrade на том же соединении."""
                return inspect(conn).get_table_names(schema=self.schemas[0])

            unique = await connection.run_sync(unique_constraints)
            self.assertEqual(unique["uq_packaging_types_code"], ("code",))
            self.assertEqual(
                set(migration_metadata().tables["packaging_types"].columns.keys()),
                {"id", "code", "name", "is_active"},
            )
            migrator = TenantMigrator()
            self.assertEqual(
                await migrator.current(connection, self.schemas[0]),
                (migrator.head(),),
            )
            await migrator.downgrade(
                connection, self.schemas[0], "0019_inventory_warehouses"
            )
            names = await connection.run_sync(table_names)
            self.assertNotIn("packaging_types", names)
            self.assertIn("warehouses", names)
            await migrator.upgrade(connection, self.schemas[0])
            names = await connection.run_sync(table_names)
            self.assertIn("packaging_types", names)
        self.assertEqual((await self.create("BOX")).status_code, 201)

    async def test_database_rejects_blank_fields_without_application(self) -> None:
        """CHECK и NOT NULL защищают таблицу при прямом обходе Domain."""
        for values in (
            {"code": " ", "name": "Name"},
            {"code": "BOX", "name": " "},
            {"code": "BOX", "name": "Name", "is_active": None},
        ):
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                statement = insert(PackagingTypeModel).values(
                    {"id": uuid4(), "is_active": True, **values}
                )
                with self.assertRaises(IntegrityError):
                    await connection.execute(statement)
                await connection.rollback()
        self.assertEqual(await self.count(), 0)
