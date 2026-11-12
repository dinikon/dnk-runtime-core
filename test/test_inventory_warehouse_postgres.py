"""HTTP, ограничения и атомарность нового склада на одноразовом PostgreSQL."""

import asyncio

from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, event, func, inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
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
from src.modules.inventory.presentation.warehouse.router import router
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
class WarehousePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Использует настоящие миграции, auth, CSRF, Depends и общий UoW."""

    async def asyncSetUp(self) -> None:
        """Создаёт два tenant и приложение с настоящими адаптерами складов."""
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], poolclass=NullPool
        )
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schemas = [
            self.naming.schema_name(tenant) for tenant in (self.tenant, self.other)
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
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = "/api/console/inventory/warehouses"

    async def drop_schemas(self) -> None:
        """Удаляет только схемы текущего теста."""
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )

    async def create(self, code: str, name: str = "Основной склад") -> Response:
        """Создаёт склад через публичный HTTP-контракт."""
        return await self.client.post(
            self.url, headers=self.headers, json={"code": code, "name": name}
        )

    async def counts(self) -> tuple[int, int]:
        """Читает число карточек и адресов своего tenant после завершения HTTP-UoW."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                roots = (
                    await session.execute(
                        select(func.count()).select_from(WarehouseModel)
                    )
                ).scalar_one()
                locations = (
                    await session.execute(
                        select(func.count()).select_from(StockLocationModel)
                    )
                ).scalar_one()
                return roots, locations

    async def test_creation_roundtrip_defaults_and_tenant_isolation(self) -> None:
        """Создаёт полную пару, сохраняет канонический код и изолирует чужие UUID."""
        response = await self.create(" Straße-001 ", "  Основной склад  ")
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(
            (body["code"], body["name"], body["is_active"]),
            ("strasse-001", "Основной склад", True),
        )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                location = (await session.scalars(select(StockLocationModel))).one()
                self.assertEqual(str(location.id), body["default_storage_location_id"])
                self.assertEqual(str(location.warehouse_id), body["id"])
                self.assertEqual(
                    (
                        location.code,
                        location.name,
                        location.location_type,
                        location.is_active,
                        location.parent_location_id,
                    ),
                    ("storage", "Основная зона хранения", "STORAGE", True, None),
                )
        self.assertEqual(
            (await self.client.get(f"{self.url}/{body['id']}")).json(), body
        )
        self.assertEqual((await self.client.get(self.url)).json()["items"], [body])
        self.assertEqual(await self.counts(), (1, 1))
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(self.url)).json()["total"], 0)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{body['id']}")).status_code, 404
        )
        other = await self.create("STRASSE-001")
        self.assertEqual(other.status_code, 201, other.text)
        self.assertNotEqual(
            other.json()["default_storage_location_id"],
            body["default_storage_location_id"],
        )

    async def test_validation_and_security_never_persist_partial_data(self) -> None:
        """Отклоняет неподдерживаемые настройки, отсутствие контекста и CSRF."""
        for payload in (
            {},
            {"code": "a"},
            {"code": " ", "name": "Name"},
            {"code": "a", "name": "\u200bName"},
            {"code": None, "name": "Name"},
            {"code": 1, "name": "Name"},
            {"code": "a", "name": ""},
            {"code": "a", "name": "Name", "is_active": False},
            {"code": "a", "name": "Name", "default_storage_location_id": str(uuid4())},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(
                    (
                        await self.client.post(
                            self.url, headers=self.headers, json=payload
                        )
                    ).status_code,
                    422,
                )
        self.assertEqual(
            (
                await self.client.post(self.url, json={"code": "a", "name": "Name"})
            ).status_code,
            403,
        )
        for principal, status in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            self.assertEqual((await self.create("blocked")).status_code, status)
            self.assertEqual((await self.client.get(self.url)).status_code, status)
            self.assertEqual(
                (await self.client.get(f"{self.url}/{uuid4()}")).status_code, status
            )
        self.assertEqual(await self.counts(), (0, 0))
        self.app.state.test_context = self.context
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}")).status_code, 404
        )
        self.assertEqual(
            (await self.client.get(f"{self.url}/invalid")).status_code, 422
        )
        for params in (
            {"offset": -1},
            {"limit": 0},
            {"limit": 101},
            {"is_active": "invalid"},
        ):
            self.assertEqual(
                (await self.client.get(self.url, params=params)).status_code, 422
            )

    async def test_list_filters_literal_search_order_and_empty_pages(self) -> None:
        """Совмещает поиск по коду/названию с активностью, пагинацией и общим total."""
        for code, name in (
            ("zeta", "КИЇВ"),
            ("BETA", "Reserve"),
            ("alpha", "Main"),
            ("x%_y", "Literal"),
        ):
            self.assertEqual((await self.create(code, name)).status_code, 201)
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(WarehouseModel)
                .where(WarehouseModel.code == "beta")
                .values(is_active=False)
            )
        page = (
            await self.client.get(self.url, params={"offset": 1, "limit": 2})
        ).json()
        self.assertEqual([item["code"] for item in page["items"]], ["beta", "x%_y"])
        self.assertEqual(page["total"], 4)
        for params, expected in (
            ({"search": "  київ  "}, ["zeta"]),
            ({"search": "%_"}, ["x%_y"]),
            ({"search": " BETA ", "is_active": False}, ["beta"]),
            ({"search": "beta", "is_active": True}, []),
            ({"search": " reserve "}, ["beta"]),
            ({"search": "absent"}, []),
        ):
            with self.subTest(params=params):
                body = (await self.client.get(self.url, params=params)).json()
                self.assertEqual([item["code"] for item in body["items"]], expected)
                self.assertEqual(body["total"], len(expected))
        empty = (await self.client.get(self.url, params={"offset": 100})).json()
        self.assertEqual((empty["items"], empty["total"]), ([], 4))

    async def test_concurrent_duplicate_code_is_atomic(self) -> None:
        """Две конкурирующие команды сохраняют ровно один склад с одной локацией."""
        responses = await asyncio.gather(
            self.create("Straße"), self.create(" STRASSE ")
        )
        self.assertEqual(
            sorted(response.status_code for response in responses),
            [201, 409],
            [response.text for response in responses],
        )
        self.assertEqual(await self.counts(), (1, 1))

    async def test_failures_during_location_and_assignment_roll_back_both(self) -> None:
        """Технический отказ до/после адреса и после назначения не оставляет частичных данных."""
        original_add = SqlAlchemyStockLocationRepository.add
        original_save = SqlAlchemyWarehouseRepository.save

        async def before_location(
            adapter: SqlAlchemyStockLocationRepository, location: StockLocation
        ) -> None:
            """Имитирует отказ записи адреса до отправки INSERT."""
            raise RuntimeError("location unavailable")

        async def after_location(
            adapter: SqlAlchemyStockLocationRepository, location: StockLocation
        ) -> None:
            """Имитирует отказ после реального INSERT адреса."""
            await original_add(adapter, location)
            raise RuntimeError("after location")

        async def after_assignment(
            adapter: SqlAlchemyWarehouseRepository, warehouse: Warehouse
        ) -> None:
            """Имитирует отказ после реального UPDATE основной ссылки."""
            await original_save(adapter, warehouse)
            raise RuntimeError("after assignment")

        for owner, method, replacement in (
            (SqlAlchemyStockLocationRepository, "add", before_location),
            (SqlAlchemyStockLocationRepository, "add", after_location),
            (SqlAlchemyWarehouseRepository, "save", after_assignment),
        ):
            with (
                self.subTest(stage=replacement.__name__),
                patch.object(owner, method, replacement),
            ):
                response = await self.create("rollback")
                self.assertEqual(response.status_code, 500, response.text)
            self.assertEqual(await self.counts(), (0, 0))

    async def test_commit_failure_does_not_return_success(self) -> None:
        """Реальный путь отказа commit откатывает карточку, адрес и ссылку."""

        def fail_commit(session: Session) -> None:
            """Прерывает commit после завершения сценария."""
            raise RuntimeError("commit unavailable")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with self.assertLogs(
                "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
                level="ERROR",
            ):
                response = await self.create("rollback-commit")
        finally:
            event.remove(Session, "before_commit", fail_commit)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.counts(), (0, 0))

    async def test_database_rejects_foreign_default_parent_and_deletion(self) -> None:
        """Составные FK защищают принадлежность, а RESTRICT сохраняет ссылки."""
        first, second = (await self.create("one")).json(), (
            await self.create("two")
        ).json()
        first_id, second_location = UUID(first["id"]), UUID(
            second["default_storage_location_id"]
        )
        first_location = UUID(first["default_storage_location_id"])
        statements = (
            update(WarehouseModel)
            .where(WarehouseModel.id == first_id)
            .values(default_storage_location_id=second_location),
            update(StockLocationModel)
            .where(StockLocationModel.id == first_location)
            .values(parent_location_id=second_location),
            update(StockLocationModel)
            .where(StockLocationModel.id == first_location)
            .values(parent_location_id=first_location),
            delete(StockLocationModel).where(StockLocationModel.id == first_location),
            delete(WarehouseModel).where(WarehouseModel.id == first_id),
        )
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            for statement in statements:
                with (
                    self.subTest(statement=statement),
                    self.assertRaises(IntegrityError),
                ):
                    async with connection.begin_nested():
                        await connection.execute(statement)
        self.assertEqual(await self.counts(), (2, 2))
        self.assertEqual(
            (await self.client.get(f"{self.url}/{first['id']}")).json(), first
        )

    async def test_revision_roundtrip_preserves_inventory_items(self) -> None:
        """Откат новой ревизии не затрагивает SKU и позволяет повторить создание склада."""
        item = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "retained"},
        )
        self.assertEqual(item.status_code, 201, item.text)
        self.assertEqual((await self.create("before")).status_code, 201)
        async with self.engine.begin() as connection:
            migrator = TenantMigrator()
            await migrator.downgrade(
                connection, self.schemas[0], "0018_catalog_inventory_items"
            )
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema=self.schemas[0])
            )
            self.assertNotIn("warehouses", tables)
            self.assertNotIn("stock_locations", tables)
            self.assertIn("inventory_items", tables)
            await migrator.upgrade(connection, self.schemas[0])
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/inventory/items/{item.json()['id']}"
                )
            ).status_code,
            200,
        )
        self.assertEqual(await self.counts(), (0, 0))
        self.assertEqual((await self.create("after")).status_code, 201)


class WarehouseRoutingTests(unittest.TestCase):
    """Проверяет регистрацию маршрутов во внешней сборке приложения."""

    def test_console_router_publishes_separate_contracts(self) -> None:
        """OpenAPI главного router содержит три метода и отдельные response schema."""
        from fastapi import FastAPI
        from src.modules.router import router as console_router

        app = FastAPI()
        app.include_router(console_router)
        paths = app.openapi()["paths"]
        self.assertEqual(
            set(paths["/api/console/inventory/warehouses"]), {"post", "get"}
        )
        self.assertEqual(
            set(paths["/api/console/inventory/warehouses/{warehouse_id}"]),
            {"get", "put", "patch"},
        )
        self.assertIn(
            "PutWarehouseResponse",
            str(paths["/api/console/inventory/warehouses/{warehouse_id}"]["put"]),
        )
        self.assertIn(
            "PatchWarehouseResponse",
            str(paths["/api/console/inventory/warehouses/{warehouse_id}"]["patch"]),
        )
        self.assertIn(
            "CreateWarehouseResponse",
            str(paths["/api/console/inventory/warehouses"]["post"]),
        )
        self.assertIn(
            "ListWarehousesResponse",
            str(paths["/api/console/inventory/warehouses"]["get"]),
        )
