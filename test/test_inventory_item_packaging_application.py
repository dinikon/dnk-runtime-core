"""Сценарии упаковок товара используют существующие Domain-правила и порты."""

from dataclasses import replace
from decimal import Decimal
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.application.inventory_item.command.add_item_packaging.command import (
    AddItemPackagingCommand,
)
from src.modules.inventory.application.inventory_item.command.add_item_packaging.handler import (
    AddItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.handler import (
    GetItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.query import (
    GetItemPackagingQuery,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.handler import (
    ListItemPackagingsHandler,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.query import (
    ListItemPackagingsQuery,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemConflictError,
    InventoryItemNotFoundError,
    InventoryItemComponentNotFoundError,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO


class ItemPackagingApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет координацию двух корней, Domain-отказы и отдельное чтение."""

    def setUp(self) -> None:
        """Готовит неизменяемые корни и изолированные порты без инфраструктуры."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()), sku=SkuVO("item")
        )
        self.item = self.item.add_barcode(
            ItemBarcode.create(
                identifier=ItemBarcodeIdVO(uuid4()), barcode=BarcodeVO("0001")
            )
        )
        self.kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BOX"),
            name=PackagingNameVO("Ящик"),
        )
        self.items = Mock(
            get_for_update=AsyncMock(return_value=self.item), save=AsyncMock()
        )
        self.types = Mock(get_for_update=AsyncMock(return_value=self.kind))
        self.identifier = uuid4()
        self.uuid = Mock(new=Mock(return_value=self.identifier))
        self.handler = AddItemPackagingHandler(self.items, self.types, self.uuid)
        self.command = AddItemPackagingCommand(
            self.item.id, self.kind.id, " BOX-12 ", " Ящик ", Decimal("12"), "PCS"
        )

    async def test_add_uses_domain_and_locks_item_before_type(self) -> None:
        """Сохраняет новую Entity, штрихкод и исходный агрегат с правильным порядком блокировок."""
        order = Mock()
        order.attach_mock(self.items.get_for_update, "item")
        order.attach_mock(self.types.get_for_update, "kind")
        result = await self.handler.execute(self.command)
        self.assertEqual([call[0] for call in order.mock_calls], ["item", "kind"])
        saved = self.items.save.await_args.args[0]
        self.assertEqual(saved.barcodes, self.item.barcodes)
        self.assertEqual(self.item.packagings, ())
        self.assertEqual(
            (result.id, result.code, result.name, result.content_quantity),
            (self.identifier, "BOX-12", "Ящик", Decimal(12)),
        )
        self.assertEqual(saved.packagings[0].id.uuid, self.identifier)
        self.assertEqual(result.inventory_item_id, self.item.id.uuid)

    async def test_missing_roots_do_not_persist(self) -> None:
        """Отсутствующий товар останавливает сценарий до чтения типа и генерации ID."""
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.types.get_for_update.assert_not_awaited()
        self.uuid.new.assert_not_called()
        self.items.get_for_update.return_value = self.item
        self.types.get_for_update.return_value = None
        with self.assertRaises(PackagingTypeNotFoundError):
            await self.handler.execute(self.command)
        self.items.save.assert_not_awaited()

    async def test_inactive_type_and_duplicate_code_are_domain_conflicts(self) -> None:
        """Неактивность и повтор кода отклоняются агрегатом до сохранения."""
        self.types.get_for_update.return_value = self.kind.deactivate()
        with self.assertRaises(InventoryItemConflictError):
            await self.handler.execute(self.command)
        self.types.get_for_update.return_value = self.kind
        await self.handler.execute(self.command)
        saved = self.items.save.await_args.args[0]
        self.items.get_for_update.return_value = saved
        self.items.save.reset_mock()
        self.uuid.new.return_value = uuid4()
        with self.assertRaises(InventoryItemConflictError):
            await self.handler.execute(self.command)
        self.items.save.assert_not_awaited()

    async def test_invalid_content_and_units_are_rejected_by_domain(self) -> None:
        """Отрицательное, некратное, неизвестное и чужая размерность не доходят до записи."""
        for changes in (
            {"content_quantity": Decimal(0)},
            {"content_quantity": Decimal("-1")},
            {"content_quantity": Decimal("0.5")},
            {"content_uom": "KG"},
            {"content_uom": "UNKNOWN"},
            {"code": " "},
            {"name": "\u200bName"},
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                await self.handler.execute(replace(self.command, **changes))
        self.items.save.assert_not_awaited()

    async def test_reads_use_query_port_and_distinguish_empty_parent(self) -> None:
        """Handlers возвращают конкретную проекцию без write-портов и нормализуют поиск."""
        projection = Mock()
        port = Mock(
            item_exists=AsyncMock(return_value=True),
            list=AsyncMock(return_value=projection),
            get_details=AsyncMock(return_value=projection),
        )
        result = await ListItemPackagingsHandler(port).execute(
            ListItemPackagingsQuery(self.item.id, search=" BOX ")
        )
        self.assertIs(result, projection)
        self.assertEqual(port.list.await_args.args[0].search, "BOX")
        query = GetItemPackagingQuery(self.item.id, ItemPackagingIdVO(self.identifier))
        self.assertIs(await GetItemPackagingHandler(port).execute(query), projection)
        port.get_details.return_value = None
        with self.assertRaises(InventoryItemComponentNotFoundError):
            await GetItemPackagingHandler(port).execute(query)
        port.item_exists.return_value = False
        with self.assertRaises(InventoryItemNotFoundError):
            await ListItemPackagingsHandler(port).execute(
                ListItemPackagingsQuery(self.item.id)
            )
