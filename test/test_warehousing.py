"""Инварианты Warehouse, сценарии и SQL-проекции первого среза."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from src.modules.reference_data.application.time_zone.query.check_time_zone.handler import (
    CheckTimeZoneHandler,
)
from src.modules.reference_data.application.time_zone.query.check_time_zone.query import (
    CheckTimeZoneQuery,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
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
from src.modules.warehousing.application.warehouse.query.list_warehouses.cursor import (
    WarehouseListCursor,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.dto import (
    ListWarehouseItemDTO,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListParametersError,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.handler import (
    ListWarehousesHandler,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.warehousing.domain.warehouse.aggregate import Warehouse
from src.modules.warehousing.domain.warehouse.error import (
    InvalidWarehouseCodeError,
    InvalidWarehouseStateError,
    InvalidWarehouseTimezoneError,
    InvalidWarehouseTitleError,
    InvalidWarehouseTypeError,
    WarehouseCodeAlreadyExistsError,
    WarehouseNotFoundError,
)
from src.modules.warehousing.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.domain.warehouse.value_object.policy import (
    WarehousePolicyVO,
)
from src.modules.warehousing.domain.warehouse.value_object.status import WarehouseStatus
from src.modules.warehousing.infrastructure.adapter.time_zone_reader import (
    ReferenceDataTimeZoneReader,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.mapper import (
    WarehouseMapper,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.query_repository import (
    SqlAlchemyWarehouseQueryRepository,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.repository import (
    SqlAlchemyWarehouseRepository,
)


def warehouse(timezone_is_active: bool = True) -> Warehouse:
    """Создаёт валидный склад для проверок публичных фабрик и сценариев."""
    return Warehouse.create(
        warehouse_id=WarehouseIdVO(uuid4()),
        code=" wh-01 ",
        title=" Основной ",
        warehouse_type=" storage ",
        policy=WarehousePolicyVO("Europe/Kyiv"),
        timezone_is_active=timezone_is_active,
        actor_id=EntityIdVO(uuid4()),
        now=datetime(2026, 10, 9, tzinfo=UTC),
    )


class WarehouseDomainTests(unittest.TestCase):
    """Проверяет собственные значения и инварианты агрегата."""

    def test_creation_requires_active_timezone_fact(self) -> None:
        """Решение по неактивному timezone принимает фабрика, а не Application."""
        with self.assertRaises(InvalidWarehouseTimezoneError):
            warehouse(timezone_is_active=False)

    def test_creation_and_immutable_values(self) -> None:
        """Создание нормализует поля и задаёт начальный статус, ревизию и аудит."""
        item = warehouse()
        self.assertEqual(
            (item.code.value, item.title.value, item.warehouse_type.value),
            ("WH-01", "Основной", "storage"),
        )
        self.assertEqual((item.status, item.revision), (WarehouseStatus.ACTIVE, 1))
        self.assertEqual(item.created_at, item.updated_at)
        self.assertEqual(item.created_by, item.updated_by)
        self.assertIs(item.created_at.tzinfo, UTC)
        self.assertEqual(WarehouseCodeVO("Wh-01"), WarehouseCodeVO("WH-01"))
        with self.assertRaises(FrozenInstanceError):
            item.code.value = "OTHER"

    def test_value_boundaries_and_invalid_values(self) -> None:
        """Отклоняет пустые, длинные, нетипизированные и NUL-значения без усечения."""
        item = warehouse()
        values = WarehouseMapper.to_insert_values(item)
        for field, error, maximum in (
            ("code", InvalidWarehouseCodeError, 64),
            ("title", InvalidWarehouseTitleError, 255),
            ("type", InvalidWarehouseTypeError, 64),
            ("timezone", InvalidWarehouseTimezoneError, 128),
        ):
            for invalid in (" ", "x" * (maximum + 1), None, "bad\x00value"):
                with self.subTest(field=field, invalid=invalid):
                    with self.assertRaises(error):
                        WarehouseMapper.to_domain({**values, field: invalid})
            restored = WarehouseMapper.to_domain({**values, field: "x" * maximum})
            self.assertIsInstance(restored, Warehouse)
        with self.assertRaises(InvalidWarehouseCodeError):
            WarehouseCodeVO("ß" * 64)

    def test_restore_preserves_state_and_uses_factory(self) -> None:
        """Mapper восстанавливает старый аудит и ревизию через restore, без create."""
        values = WarehouseMapper.to_insert_values(warehouse())
        values.update(
            status="inactive",
            revision=7,
            updated_at=values["created_at"] + timedelta(days=1),
        )
        with (
            patch.object(
                Warehouse, "create", side_effect=AssertionError("create during restore")
            ),
            patch.object(Warehouse, "restore", wraps=Warehouse.restore) as restore,
        ):
            restored = WarehouseMapper.to_domain(values)
        restore.assert_called_once()
        self.assertEqual(
            (restored.status, restored.revision), (WarehouseStatus.INACTIVE, 7)
        )
        self.assertEqual(WarehouseMapper.to_insert_values(restored), values)

    def test_aggregate_rejects_invalid_audit_revision_and_status(self) -> None:
        """Проверки агрегата выполняются его фабрикой даже при прямом restore."""
        values = WarehouseMapper.to_insert_values(warehouse())
        for changes in (
            {"revision": 0},
            {"revision": True},
            {"revision": 1.5},
            {"status": "unknown"},
            {"created_at": datetime(2026, 10, 9)},
            {"updated_at": values["created_at"] - timedelta(seconds=1)},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidWarehouseStateError),
            ):
                WarehouseMapper.to_domain({**values, **changes})
        local = datetime(2026, 10, 9, 3, tzinfo=timezone(timedelta(hours=3)))
        restored = WarehouseMapper.to_domain(
            {**values, "created_at": local, "updated_at": local}
        )
        self.assertEqual(restored.created_at, values["created_at"])
        self.assertIs(restored.created_at.tzinfo, UTC)


class WarehouseApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет orchestration, публичный timezone-контракт и cursor-пагинацию."""

    def test_cursor_round_trips_long_unicode_codes(self) -> None:
        """Максимальные Unicode-коды не создают непригодный next_cursor."""
        for code in ("Я" * 64, "😀" * 64, "A" + "\x01" * 63):
            with self.subTest(code=code):
                cursor = WarehouseListCursor(WarehouseCodeVO(code).value, uuid4())
                self.assertEqual(WarehouseListCursor.decode(cursor.encode()), cursor)

    async def test_creation_checks_timezone_and_passes_tenant(self) -> None:
        """Запись получает агрегат и доверенный tenant после проверки timezone."""
        tenant, actor, identifier = EntityIdVO(uuid4()), EntityIdVO(uuid4()), uuid4()
        repository = Mock(add=AsyncMock())
        zones = Mock(is_active=AsyncMock(return_value=True))
        handler = CreateWarehouseHandler(
            repository=repository,
            time_zones=zones,
            clock=Mock(now=Mock(return_value=datetime(2026, 10, 9, tzinfo=UTC))),
            uuid_generator=Mock(new=Mock(return_value=identifier)),
        )
        command = CreateWarehouseCommand(
            tenant, actor, " wh-01 ", "Склад", "storage", " Europe/Kyiv "
        )
        result = await handler.execute(command)
        self.assertEqual(
            (result.id, result.code, result.status, result.revision),
            (identifier, "WH-01", "active", 1),
        )
        zones.is_active.assert_awaited_once_with("Europe/Kyiv")
        written = repository.add.await_args.kwargs
        self.assertEqual(written["tenant_id"], tenant)
        self.assertEqual(written["warehouse"].created_by, actor)
        zones.is_active.return_value = False
        repository.add.reset_mock()
        with self.assertRaises(InvalidWarehouseTimezoneError):
            await handler.execute(command)
        repository.add.assert_not_awaited()
        with self.assertRaises(FrozenInstanceError):
            command.code = "OTHER"

    async def test_public_timezone_reader_checks_one_active_record(self) -> None:
        """Межмодульный адаптер возвращает bool из собственного публичного DTO."""
        session = Mock(scalar=AsyncMock(return_value="Europe/Kyiv"))
        handler = CheckTimeZoneHandler(SqlAlchemyCatalogRepository(session))
        adapter = ReferenceDataTimeZoneReader(handler)
        self.assertTrue(await adapter.is_active("Europe/Kyiv"))
        sql = str(session.scalar.await_args.args[0].compile())
        self.assertIn("ref_time_zones", sql)
        self.assertIn("active IS true", sql)
        session.scalar.return_value = None
        result = await handler.execute(CheckTimeZoneQuery("Unknown/Zone"))
        self.assertEqual((result.code, result.is_active), ("Unknown/Zone", False))

    async def test_get_not_found_and_page_continuation(self) -> None:
        """Отсутствие даёт бизнес-ошибку; next_cursor указывает последнюю видимую строку."""
        tenant = EntityIdVO(uuid4())
        repository = Mock(
            get_details=AsyncMock(return_value=None), list_items=AsyncMock()
        )
        with self.assertRaises(WarehouseNotFoundError):
            await GetWarehouseHandler(repository).execute(
                GetWarehouseQuery(tenant, WarehouseIdVO(uuid4()))
            )
        rows = tuple(
            ListWarehouseItemDTO(uuid4(), code, code, "storage", "active", 1)
            for code in ("A", "B", "C")
        )
        repository.list_items.return_value = rows
        handler = ListWarehousesHandler(repository)
        result = await handler.execute(
            ListWarehousesQuery(
                tenant, status="active", warehouse_type=" storage ", limit=2
            )
        )
        self.assertEqual(result.items, rows[:2])
        self.assertEqual(
            WarehouseListCursor.decode(result.next_cursor),
            WarehouseListCursor("B", rows[1].id),
        )
        repository.list_items.return_value = rows[2:]
        last = await handler.execute(
            ListWarehousesQuery(tenant, cursor=result.next_cursor, limit=2)
        )
        self.assertEqual(last.items, rows[2:])
        self.assertIsNone(last.next_cursor)
        self.assertEqual(repository.list_items.await_args.kwargs["cursor"].code, "B")
        repository.list_items.return_value = ()
        empty = await handler.execute(ListWarehousesQuery(tenant))
        self.assertEqual(empty.items, ())
        self.assertIsNone(empty.next_cursor)

    async def test_bad_list_parameters_never_read_repository(self) -> None:
        """Неверные фильтры и повреждённые курсоры отвергаются до SQL."""
        repository = Mock(list_items=AsyncMock())
        handler = ListWarehousesHandler(repository)
        query = ListWarehousesQuery(EntityIdVO(uuid4()))
        bad_cursor = WarehouseListCursor("lowercase", uuid4()).encode()
        for changes in (
            {"limit": 0},
            {"limit": 101},
            {"limit": True},
            {"status": "bogus"},
            {"cursor": ""},
            {"cursor": "!!!"},
            {"cursor": "W10"},
            {"cursor": bad_cursor},
            {"cursor": "x" * 1025},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidWarehouseListParametersError),
            ):
                await handler.execute(replace(query, **changes))
        with self.assertRaises(InvalidWarehouseTypeError):
            await handler.execute(replace(query, warehouse_type=" "))
        repository.list_items.assert_not_awaited()


class WarehousePersistenceTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет атомарность INSERT и явную SQL-проекцию без Domain restore."""

    async def test_insert_is_single_atomic_statement(self) -> None:
        """Уникальный код проверяется самой вставкой, без предварительного SELECT."""
        result = Mock()
        result.scalar_one_or_none.return_value = uuid4()
        session = Mock(execute=AsyncMock(return_value=result))
        repository = SqlAlchemyWarehouseRepository(session)
        await repository.add(tenant_id=EntityIdVO(uuid4()), warehouse=warehouse())
        sql = str(
            session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
        )
        self.assertIn(
            "ON CONFLICT ON CONSTRAINT uq_warehousing_warehouses_code DO NOTHING", sql
        )
        self.assertIn("RETURNING tenant.warehousing_warehouses.id", sql)
        self.assertEqual(session.execute.await_count, 1)
        result.scalar_one_or_none.return_value = None
        with self.assertRaises(WarehouseCodeAlreadyExistsError):
            await repository.add(tenant_id=EntityIdVO(uuid4()), warehouse=warehouse())

    async def test_list_projects_and_filters_without_restore(self) -> None:
        """Read repository читает только поля списка и применяет keyset/limit."""
        values = WarehouseMapper.to_insert_values(warehouse())
        result = MagicMock()
        result.mappings.return_value.__iter__.return_value = iter([values])
        session = Mock(execute=AsyncMock(return_value=result))
        repository = SqlAlchemyWarehouseQueryRepository(session)
        warehouse_type = warehouse().warehouse_type
        with patch.object(
            Warehouse, "restore", side_effect=AssertionError("Domain restore in query")
        ):
            items = await repository.list_items(
                tenant_id=EntityIdVO(uuid4()),
                status=WarehouseStatus.ACTIVE,
                warehouse_type=warehouse_type,
                cursor=WarehouseListCursor("A", uuid4()),
                limit=3,
            )
        self.assertEqual(items[0].code, "WH-01")
        statement = session.execute.await_args.args[0]
        self.assertEqual(
            set(statement.selected_columns.keys()),
            {"id", "code", "title", "type", "status", "revision"},
        )
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn(
            "ORDER BY tenant.warehousing_warehouses.code, tenant.warehousing_warehouses.id",
            sql,
        )
        self.assertIn(") > (", sql)
        self.assertIn("LIMIT", sql)
