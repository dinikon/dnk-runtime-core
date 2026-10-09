"""Реальный PostgreSQL: миграции, tenant-изоляция, keyset и конкурентный код."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import os
import unittest
from unittest.mock import Mock
from uuid import UUID, uuid4

from alembic import command
from sqlalchemy import func, inspect, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

import src.modules.persistence
from src.modules.reference_data.application.time_zone.query.check_time_zone.handler import (
    CheckTimeZoneHandler,
)
from src.modules.reference_data.infrastructure.persistence.models.time_zone import (
    TimeZoneModel,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.base import Base
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.warehousing.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
)
from src.modules.warehousing.application.warehouse.command.create_warehouse.dto import (
    CreateWarehouseResultDTO,
)
from src.modules.warehousing.application.warehouse.command.create_warehouse.handler import (
    CreateWarehouseHandler,
)
from src.modules.warehousing.application.warehouse.query.get_warehouse.handler import (
    GetWarehouseHandler,
)
from src.modules.warehousing.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.handler import (
    ListWarehousesHandler,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.warehousing.domain.warehouse.error import (
    WarehouseCodeAlreadyExistsError,
    WarehouseNotFoundError,
)
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.infrastructure.adapter.time_zone_reader import (
    ReferenceDataTimeZoneReader,
)
from src.modules.warehousing.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.query_repository import (
    SqlAlchemyWarehouseQueryRepository,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL 16 database."
)
class WarehousingPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет поведение на одноразовой БД и удаляет только собственные схемы."""

    async def asyncSetUp(self) -> None:
        """Создаёт global metadata и известный активный timezone для настоящего порта."""
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.migrator = TenantMigrator()
        self.schemas: list[str] = []
        self.tenant = EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.now = datetime(2026, 10, 9, tzinfo=UTC)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                insert(TimeZoneModel)
                .values(code="UTC", active=True)
                .on_conflict_do_nothing()
            )

    async def asyncTearDown(self) -> None:
        """Удаляет созданные этим тестом схемы и закрывает engine."""
        try:
            async with self.engine.begin() as connection:
                for schema in self.schemas:
                    await connection.execute(
                        DropSchema(schema, cascade=True, if_exists=True)
                    )
        finally:
            await self.engine.dispose()

    async def new_schema(self, revision: str | None = None) -> str:
        """Создаёт уникальную tenant-схему и применяет заданную ревизию или head."""
        schema = "dnk_wh_" + uuid4().hex
        self.schemas.append(schema)
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            if revision is None:
                await self.migrator.upgrade(connection, schema)
            else:
                await self.migrator._migrate(
                    connection, schema, command.upgrade, revision
                )
        return schema

    @asynccontextmanager
    async def session(self, schema: str) -> AsyncIterator[AsyncSession]:
        """Открывает один UoW на соединении с внешне заданной tenant-схемой."""
        async with self.engine.connect() as connection:
            await connection.execution_options(schema_translate_map={"tenant": schema})
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow.session

    def create_handler(
        self, session: AsyncSession, identifier: UUID
    ) -> CreateWarehouseHandler:
        """Собирает реальные репозитории и публичный timezone reader на одной session."""
        return CreateWarehouseHandler(
            repository=SqlAlchemyWarehouseRepository(session),
            time_zones=ReferenceDataTimeZoneReader(
                CheckTimeZoneHandler(SqlAlchemyCatalogRepository(session))
            ),
            clock=Mock(now=Mock(return_value=self.now)),
            uuid_generator=Mock(new=Mock(return_value=identifier)),
        )

    async def create(
        self,
        schema: str,
        *,
        code: str,
        identifier: UUID | None = None,
        title: str = "Склад",
        warehouse_type: str = "storage",
    ) -> CreateWarehouseResultDTO:
        """Создаёт и коммитит склад через полный Application-сценарий."""
        async with self.session(schema) as session:
            return await self.create_handler(session, identifier or uuid4()).execute(
                CreateWarehouseCommand(
                    tenant_id=self.tenant,
                    actor_id=self.actor,
                    code=code,
                    title=title,
                    warehouse_type=warehouse_type,
                    timezone="UTC",
                )
            )

    async def test_new_tenant_and_upgrade_downgrade_from_inventory_removal(
        self,
    ) -> None:
        """Новый head создаёт только новую таблицу; upgrade/downgrade изолированы по tenant."""
        fresh = await self.new_schema()
        upgraded = await self.new_schema("0016_remove_inventory")
        async with self.engine.begin() as connection:
            self.assertEqual(
                await self.migrator.current(connection, fresh),
                ("0017_warehousing_warehouses",),
            )
            before = await connection.run_sync(
                lambda conn: set(inspect(conn).get_table_names(schema=upgraded))
            )
            self.assertNotIn("warehousing_warehouses", before)
            self.assertTrue({"skus", "warehouses"}.isdisjoint(before))
            await self.migrator.upgrade(connection, upgraded)
            await self.migrator.upgrade(connection, upgraded)
            after = await connection.run_sync(
                lambda conn: set(inspect(conn).get_table_names(schema=upgraded))
            )
            self.assertEqual(after, before | {"warehousing_warehouses"})
            constraints = await connection.run_sync(
                lambda conn: inspect(conn).get_unique_constraints(
                    "warehousing_warehouses", schema=upgraded
                )
            )
            self.assertIn(
                "uq_warehousing_warehouses_code", {item["name"] for item in constraints}
            )
            await self.migrator.downgrade(connection, upgraded, "0016_remove_inventory")
            restored = await connection.run_sync(
                lambda conn: set(inspect(conn).get_table_names(schema=upgraded))
            )
            self.assertEqual(restored, before)
            self.assertEqual(
                await self.migrator.current(connection, fresh),
                ("0017_warehousing_warehouses",),
            )

    async def test_same_code_and_uuid_in_two_tenants_and_no_foreign_reads(self) -> None:
        """Одинаковые идентификаторы и коды независимы; чужой уникальный ID не виден."""
        left, right = await self.new_schema(), await self.new_schema()
        identifier, only_left = uuid4(), uuid4()
        await self.create(left, code=" wh-01 ", identifier=identifier, title="Левый")
        await self.create(right, code="WH-01", identifier=identifier, title="Правый")
        await self.create(left, code="LEFT-ONLY", identifier=only_left)
        for schema, title in ((left, "Левый"), (right, "Правый")):
            async with self.session(schema) as session:
                restored = await SqlAlchemyWarehouseRepository(session).get(
                    tenant_id=self.tenant, warehouse_id=WarehouseIdVO(identifier)
                )
                self.assertEqual(restored.title.value, title)
                self.assertEqual((restored.code.value, restored.revision), ("WH-01", 1))
                self.assertEqual(restored.created_at, self.now)
                self.assertEqual(restored.created_by, self.actor)
        async with self.session(right) as session:
            query = SqlAlchemyWarehouseQueryRepository(session)
            with self.assertRaises(WarehouseNotFoundError):
                await GetWarehouseHandler(query).execute(
                    GetWarehouseQuery(self.tenant, WarehouseIdVO(only_left))
                )
            page = await ListWarehousesHandler(query).execute(
                ListWarehousesQuery(self.tenant)
            )
            self.assertEqual([item.title for item in page.items], ["Правый"])

    async def test_concurrent_case_variants_create_exactly_one_warehouse(self) -> None:
        """Две одновременные UoW с одним нормализованным кодом дают успех и конфликт."""
        schema = await self.new_schema()
        gate = asyncio.Event()

        async def create_after_gate(
            code: str,
        ) -> CreateWarehouseResultDTO | WarehouseCodeAlreadyExistsError:
            """Стартует конкурентное создание после общей точки синхронизации."""
            await gate.wait()
            try:
                return await self.create(schema, code=code)
            except WarehouseCodeAlreadyExistsError as exc:
                return exc

        tasks = [
            asyncio.create_task(create_after_gate(code))
            for code in ("wh-01", " WH-01 ")
        ]
        gate.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)
        self.assertEqual(
            sum(isinstance(result, CreateWarehouseResultDTO) for result in results), 1
        )
        self.assertEqual(
            sum(
                isinstance(result, WarehouseCodeAlreadyExistsError)
                for result in results
            ),
            1,
        )
        async with self.session(schema) as session:
            self.assertEqual(
                await session.scalar(select(func.count()).select_from(WarehouseModel)),
                1,
            )

    async def test_real_keyset_pagination_and_filters(self) -> None:
        """Переход по курсорам не повторяет строки и сохраняет фильтры."""
        schema = await self.new_schema()
        for code, kind in (
            ("A", "storage"),
            ("B", "retail"),
            ("C", "storage"),
            ("D", "retail"),
            ("E", "storage"),
        ):
            await self.create(schema, code=code, warehouse_type=kind)
        codes: list[str] = []
        cursor = None
        for _ in range(3):
            async with self.session(schema) as session:
                result = await ListWarehousesHandler(
                    SqlAlchemyWarehouseQueryRepository(session)
                ).execute(
                    ListWarehousesQuery(
                        self.tenant,
                        status="active",
                        warehouse_type="storage",
                        cursor=cursor,
                        limit=1,
                    )
                )
                codes.extend(item.code for item in result.items)
                cursor = result.next_cursor
        self.assertEqual(codes, ["A", "C", "E"])
        self.assertIsNone(cursor)
        async with self.session(schema) as session:
            result = await ListWarehousesHandler(
                SqlAlchemyWarehouseQueryRepository(session)
            ).execute(ListWarehousesQuery(self.tenant, status="inactive"))
            self.assertEqual(result.items, ())

    async def test_failure_after_insert_rolls_back_whole_operation(self) -> None:
        """Сбой процесса после успешной вставки не оставляет частично созданный склад."""
        schema = await self.new_schema()
        with self.assertRaisesRegex(RuntimeError, "injected"):
            async with self.session(schema) as session:
                await self.create_handler(session, uuid4()).execute(
                    CreateWarehouseCommand(
                        self.tenant, self.actor, "ROLLBACK", "Склад", "storage", "UTC"
                    )
                )
                raise RuntimeError("injected failure after insert")
        async with self.session(schema) as session:
            self.assertEqual(
                await session.scalar(select(func.count()).select_from(WarehouseModel)),
                0,
            )
