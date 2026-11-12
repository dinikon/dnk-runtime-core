from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from unittest.mock import AsyncMock

"""Сценарии обновления и удаления через порты без HTTP и SQL."""

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.inventory.application.inventory_item.command.update_inventory_item.command import (
    UpdateInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.handler import (
    UpdateInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.command.update_inventory_item.error import (
    InvalidInventoryItemUpdateError,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.command import (
    DeleteInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.handler import (
    DeleteInventoryItemHandler,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.entity.item_barcode import ItemBarcode
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.error import InventoryItemInUseError
from sqlalchemy.exc import IntegrityError
from src.modules.inventory.domain.inventory_item.value_object.barcode import BarcodeVO
from src.modules.inventory.domain.inventory_item.value_object.item_barcode_id import (
    ItemBarcodeIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from test.test_inventory_item_revision_domain import make_item


class InventoryItemMutationsApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет отсутствующие поля, дочерние ID и обработку отсутствующего корня."""

    async def asyncSetUp(self) -> None:
        """Готовит текущий агрегат с двумя штрихкодами и write-порт."""
        self.item = make_item()
        for value in ("000AbC", "000abc"):
            self.item = self.item.add_barcode(
                ItemBarcode.create(
                    identifier=ItemBarcodeIdVO(uuid4()), barcode=BarcodeVO(value)
                )
            )
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.item),
            save=AsyncMock(),
            delete=AsyncMock(),
        )
        self.ids = Mock(new=Mock(side_effect=uuid4))
        self.update = UpdateInventoryItemHandler(self.repository, self.ids)
        self.delete = DeleteInventoryItemHandler(
            self.repository,
            AsyncMock(get=AsyncMock(return_value=InventoryItemDeletionUsage(False))),
        )
        self.command = UpdateInventoryItemCommand(
            self.item.id, frozenset({"sku"}), sku=" Renamed "
        )

    async def test_partial_update_preserves_omitted_fields_and_barcodes(self) -> None:
        """Изменяет только SKU и сохраняет остальные данные вместе с дочерними ID."""
        result = await self.update.execute(self.command)
        updated = self.repository.save.await_args.args[0]
        self.assertEqual(result.sku, "renamed")
        self.assertEqual(updated.barcodes, self.item.barcodes)
        self.repository.save.assert_awaited_once_with(updated)
        self.ids.new.assert_not_called()

    async def test_delete_translates_only_catalog_fk_violation(self) -> None:
        """Защитный FK даёт предметный конфликт, неизвестная ошибка остаётся технической."""
        for constraint in ("fk_catalog_item_inventory_item", "unrelated_fk"):
            original = RuntimeError("reference violation")
            original.sqlstate = "23503"
            original.constraint_name = constraint
            failure = IntegrityError("delete", {}, original)
            repository = SqlAlchemyInventoryItemRepository(
                Mock(execute=AsyncMock(side_effect=failure))
            )
            expected = (
                InventoryItemInUseError
                if constraint == "fk_catalog_item_inventory_item"
                else IntegrityError
            )
            with self.subTest(constraint=constraint), self.assertRaises(expected):
                await repository.delete(self.item)

    async def test_collection_replacement_preserves_matching_ids_and_order(
        self,
    ) -> None:
        """Сохраняет ID по точному коду после trim и выдаёт ID только новым значениям."""
        result = await self.update.execute(
            replace(
                self.command,
                fields=frozenset({"barcodes"}),
                barcodes=(" 000abc ", "new"),
            )
        )
        self.assertEqual(result.barcodes[0].id, self.item.barcodes[1].id.uuid)
        self.assertEqual([b.barcode for b in result.barcodes], ["000abc", "new"])
        self.ids.new.assert_called_once()

    async def test_empty_collection_clears_and_noop_does_not_save(self) -> None:
        """Отличает пустую коллекцию от пропущенного поля и распознаёт нормализованный no-op."""
        result = await self.update.execute(replace(self.command, sku=" ITEM "))
        self.assertEqual(result.sku, self.item.sku.value)
        self.repository.save.assert_not_awaited()
        cleared = await self.update.execute(
            replace(self.command, fields=frozenset({"barcodes"}), barcodes=())
        )
        self.assertEqual(cleared.barcodes, ())

    async def test_full_update_changes_interdependent_settings_together(self) -> None:
        """Применяет совместимые итоговые настройки единственным доменным переходом."""
        command = replace(
            self.command,
            fields=frozenset(
                {"base_uom", "quantity_rules", "tracking_mode", "expiration_mode"}
            ),
            base_uom="KG",
            quantity_step=Decimal("0.001"),
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        result = await self.update.execute(command)
        self.assertEqual(
            (result.base_uom, result.quantity_step), ("KG", Decimal("0.001"))
        )

    async def test_invalid_commands_do_not_write(self) -> None:
        """Проверяет контракт команды вне HTTP и доменные ошибки состава."""
        for changes in (
            {"fields": frozenset()},
            {"fields": frozenset({"unknown"})},
            {"sku": None},
            {"fields": frozenset({"barcodes"}), "barcodes": None},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidInventoryItemUpdateError),
            ):
                await self.update.execute(replace(self.command, **changes))
        with self.assertRaises(InventoryError):
            await self.update.execute(
                replace(
                    self.command, fields=frozenset({"barcodes"}), barcodes=("a", " a ")
                )
            )
        self.repository.save.assert_not_awaited()

    async def test_missing_items_never_mutate_storage(self) -> None:
        """Обновление и удаление отсутствующей позиции завершаются предметной ошибкой."""
        self.repository.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.update.execute(self.command)
        with self.assertRaises(InventoryItemNotFoundError):
            await self.delete.execute(DeleteInventoryItemCommand(self.item.id))
        self.repository.save.assert_not_awaited()
        self.repository.delete.assert_not_awaited()

    async def test_delete_returns_none_and_uses_loaded_aggregate(self) -> None:
        """Удаляет загруженный агрегат без дополнительных предусловий и пустого DTO."""
        result = await self.delete.execute(DeleteInventoryItemCommand(self.item.id))
        self.assertIsNone(result)
        self.repository.delete.assert_awaited_once_with(self.item)

    async def test_missing_sql_row_stops_before_child_mutations(self) -> None:
        """Отсутствие строки в RETURNING не позволяет создать детей вместо отсутствующего корня."""
        returned = Mock(scalar_one_or_none=Mock(return_value=None))
        session = SimpleNamespace(execute=AsyncMock(return_value=returned))
        repository = SqlAlchemyInventoryItemRepository(session)
        for action in (repository.save, repository.delete):
            session.execute.reset_mock()
            with self.assertRaises(InventoryItemNotFoundError):
                await action(self.item)
            session.execute.assert_awaited_once()
