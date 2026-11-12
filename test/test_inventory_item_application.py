"""Контракты сценариев InventoryItem и преобразование ошибок write-адаптера."""

from dataclasses import replace
from decimal import Decimal
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from src.modules.inventory.application.inventory_item.query.get_inventory_item.handler import (
    GetInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.query import (
    GetInventoryItemQuery,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)

from src.modules.inventory.application.inventory_item.command.create_inventory_item.command import (
    CreateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.create_inventory_item.handler import (
    CreateInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.dto import (
    ListInventoryItemsResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.error import (
    InvalidInventoryItemListQueryError,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.handler import (
    ListInventoryItemsHandler,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.query import (
    ListInventoryItemsQuery,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemBarcodeAlreadyExistsError,
    InventoryItemSkuAlreadyExistsError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)


class InventoryItemApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет наблюдаемое поведение обоих сценариев через их порты."""

    async def asyncSetUp(self) -> None:
        """Готовит независимые порты и детерминированные идентификаторы."""
        self.identifiers = [uuid4(), uuid4(), uuid4()]
        self.repository = Mock(add=AsyncMock())
        self.uuid_generator = Mock(new=Mock(side_effect=self.identifiers))
        self.handler = CreateInventoryItemHandler(self.repository, self.uuid_generator)
        self.command = CreateInventoryItemCommand(
            sku="  Straße-01  ",
            base_uom="KG",
            quantity_step=Decimal("0.0000000000000000000000000123"),
            barcodes=(" 000AbC ", "000abc"),
        )

    async def test_create_preserves_exact_values_and_child_identity(self) -> None:
        """Проверяет нормализацию, точный шаг и серверные ID полного агрегата."""
        result = await self.handler.execute(self.command)
        item = self.repository.add.await_args.args[0]
        self.assertIsInstance(item, InventoryItem)
        self.assertEqual(result.id, self.identifiers[0])
        self.assertEqual(result.sku, "strasse-01")
        self.assertEqual(result.quantity_step, self.command.quantity_step)
        self.assertEqual(
            [barcode.id for barcode in result.barcodes], self.identifiers[1:]
        )
        self.assertEqual(
            [barcode.barcode for barcode in result.barcodes], ["000AbC", "000abc"]
        )
        self.assertEqual(item.packagings, ())
        self.assertEqual(result.tracking_mode, TrackingMode.NONE)
        self.assertEqual(result.expiration_mode, ExpirationMode.NONE)

    async def test_domain_rejections_never_reach_storage(self) -> None:
        """Проверяет реальные Domain-отказы до вызова write-порта."""
        invalid = (
            {"sku": " "},
            {"sku": "ß" * 13},
            {"base_uom": "UNKNOWN"},
            {"quantity_step": Decimal("0")},
            {"tracking_mode": TrackingMode.SERIAL},
            {"expiration_mode": ExpirationMode.REQUIRED},
            {"barcodes": ("0001", " 0001 ")},
        )
        for values in invalid:
            with self.subTest(values=values):
                handler = CreateInventoryItemHandler(self.repository, Mock(new=uuid4))
                with self.assertRaises(InventoryError):
                    await handler.execute(replace(self.command, **values))
        self.repository.add.assert_not_awaited()

    async def test_create_only_sku_uses_domain_defaults_and_partial_settings_override(
        self,
    ) -> None:
        """Передаёт отсутствие настроек фабрике Domain и сохраняет её полный результат."""
        handler = CreateInventoryItemHandler(self.repository, Mock(new=uuid4))
        default = await handler.execute(CreateInventoryItemCommand(sku=" Default "))
        self.assertEqual(
            (
                default.sku,
                default.base_uom,
                default.quantity_step,
                default.tracking_mode,
                default.expiration_mode,
                default.barcodes,
            ),
            (
                "default",
                "PCS",
                Decimal("1"),
                TrackingMode.NONE,
                ExpirationMode.NONE,
                (),
            ),
        )
        custom = await handler.execute(
            CreateInventoryItemCommand(
                sku="partial",
                base_uom="L",
                quantity_step=Decimal("0.12345678901234567890123456789"),
                expiration_mode=ExpirationMode.OPTIONAL,
            )
        )
        self.assertEqual(custom.base_uom, "L")
        self.assertEqual(
            custom.quantity_step, Decimal("0.12345678901234567890123456789")
        )
        self.assertEqual(custom.tracking_mode, TrackingMode.NONE)
        self.assertEqual(custom.expiration_mode, ExpirationMode.OPTIONAL)
        self.assertEqual(self.repository.add.await_count, 2)

    async def test_write_conflict_is_propagated_to_caller(self) -> None:
        """Не превращает отказ записи в успешный DTO."""
        error = InventoryItemSkuAlreadyExistsError()
        self.repository.add.side_effect = error
        with self.assertRaises(InventoryItemSkuAlreadyExistsError) as caught:
            await self.handler.execute(self.command)
        self.assertIs(caught.exception, error)

    async def test_list_normalizes_search_and_preserves_page(self) -> None:
        """Передаёт нормализованный поиск read-порту и возвращает его результат."""
        page = ListInventoryItemsResultDTO((), 7, 2, 3)
        repository = Mock(list=AsyncMock(return_value=page))
        handler = ListInventoryItemsHandler(repository)
        result = await handler.execute(ListInventoryItemsQuery(2, 3, " Straße "))
        self.assertIs(result, page)
        repository.list.assert_awaited_once_with(
            ListInventoryItemsQuery(2, 3, "strasse")
        )
        await handler.execute(ListInventoryItemsQuery(search="   "))
        self.assertIsNone(repository.list.await_args.args[0].search)

    async def test_details_returns_read_projection_or_not_found(self) -> None:
        """Читает через Application-порт, не загружая агрегат или write-порт."""
        result = GetInventoryItemResultDTO(
            uuid4(),
            "sku",
            "PCS",
            Decimal("1E-100"),
            TrackingMode.NONE,
            ExpirationMode.NONE,
            (),
        )
        repository = Mock(get_details=AsyncMock(return_value=result))
        query = GetInventoryItemQuery(InventoryItemIdVO(result.id))
        handler = GetInventoryItemHandler(repository)
        self.assertIs(await handler.execute(query), result)
        repository.get_details.assert_awaited_once_with(query)
        repository.get_details.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await handler.execute(query)

    async def test_list_rejects_invalid_input_without_http(self) -> None:
        """Защищает контракт пагинации при прямом вызове Application."""
        repository = Mock(list=AsyncMock())
        handler = ListInventoryItemsHandler(repository)
        for values in (
            {"offset": -1},
            {"offset": True},
            {"offset": 0.5},
            {"limit": 0},
            {"limit": 101},
            {"limit": True},
            {"search": 123},
        ):
            with self.subTest(values=values):
                with self.assertRaises(InvalidInventoryItemListQueryError):
                    await handler.execute(ListInventoryItemsQuery(**values))
        repository.list.assert_not_awaited()

    async def test_adapter_translates_only_known_unique_constraints(self) -> None:
        """Различает конфликты SKU/штрихкода и неожиданные ошибки БД."""
        await self.handler.execute(self.command)
        item = self.repository.add.await_args.args[0]
        for constraint, expected in (
            ("uq_inventory_items_sku", InventoryItemSkuAlreadyExistsError),
            (
                "uq_inventory_item_barcodes_barcode",
                InventoryItemBarcodeAlreadyExistsError,
            ),
            ("pk_inventory_items", IntegrityError),
        ):
            with self.subTest(constraint=constraint):
                driver = RuntimeError("driver unique violation")
                driver.constraint_name = constraint
                original = RuntimeError("asyncpg wrapper")
                original.sqlstate = "23505"
                original.__cause__ = driver
                error = IntegrityError("insert", {}, original)
                session = SimpleNamespace(
                    execute=AsyncMock(side_effect=error),
                    commit=AsyncMock(),
                    rollback=AsyncMock(),
                )
                with self.assertRaises(expected):
                    await SqlAlchemyInventoryItemRepository(session).add(item)
                session.commit.assert_not_awaited()
                session.rollback.assert_not_awaited()
