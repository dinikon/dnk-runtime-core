"""Изменение упаковки координируется через InventoryItem и существующие Domain-правила."""

from dataclasses import replace
from decimal import Decimal
import unittest
from unittest.mock import Mock
from uuid import uuid4
from src.modules.inventory.application.inventory_item.command.update_item_packaging.command import (
    UpdateItemPackagingCommand,
)
from src.modules.inventory.application.inventory_item.command.update_item_packaging.handler import (
    UpdateItemPackagingHandler,
)
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemNotFoundError,
    InventoryItemComponentNotFoundError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.domain.error import InventoryError
from test import test_inventory_item_packaging_application as support


class ItemPackagingMutationsApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет объединение PATCH, неизменность Entity и отказы без сохранения."""

    async def asyncSetUp(self) -> None:
        """Создаёт агрегат с двумя упаковками и независимым штрихкодом."""
        fixture = support.ItemPackagingApplicationTests()
        fixture.setUp()
        await fixture.handler.execute(fixture.command)
        self.identifier = ItemPackagingIdVO(fixture.identifier)
        fixture.items.get_for_update.return_value = fixture.items.save.await_args.args[
            0
        ]
        fixture.uuid.new.return_value = uuid4()
        await fixture.handler.execute(
            replace(fixture.command, code="OTHER", name="Другая")
        )
        self.item = fixture.items.save.await_args.args[0]
        self.items, self.types, self.kind = fixture.items, fixture.types, fixture.kind
        self.items.get_for_update.return_value = self.item
        self.items.save.reset_mock()
        self.items.get_for_update.reset_mock()
        self.types.get_for_update.reset_mock()
        self.handler = UpdateItemPackagingHandler(self.items, self.types)
        self.command = UpdateItemPackagingCommand(
            self.item.id, self.identifier, frozenset({"name"}), name=" Новое название "
        )

    async def test_partial_update_preserves_identity_order_and_unmentioned_fields(
        self,
    ) -> None:
        """Handler блокирует корни в нужном порядке и меняет только явно указанные значения."""
        order = Mock()
        order.attach_mock(self.items.get_for_update, "item")
        order.attach_mock(self.types.get_for_update, "kind")
        result = await self.handler.execute(
            replace(self.command, code="ignored", content_quantity=Decimal(0))
        )
        saved = self.items.save.await_args.args[0]
        self.assertEqual([c[0] for c in order.mock_calls], ["item", "kind"])
        self.types.get_for_update.assert_awaited_once_with(self.kind.id)
        self.assertEqual(
            (result.id, result.name, result.code, result.content_quantity),
            (self.identifier.uuid, "Новое название", "BOX-12", Decimal(12)),
        )
        self.assertEqual(
            [p.id for p in saved.packagings], [p.id for p in self.item.packagings]
        )
        self.assertEqual(saved.packagings[1], self.item.packagings[1])
        self.assertEqual(saved.barcodes, self.item.barcodes)
        self.assertEqual(self.item.packagings[0].name.value, "Ящик")

    async def test_full_update_changes_type_without_deriving_manual_code_or_name(
        self,
    ) -> None:
        """Итоговый тип загружается по новому ID, но код и название варианта остаются ручными."""
        kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("PALLET"),
            name=PackagingNameVO("Палета"),
        )
        self.types.get_for_update.return_value = kind
        result = await self.handler.execute(
            replace(
                self.command,
                fields=frozenset(
                    {
                        "packaging_type_id",
                        "code",
                        "name",
                        "content_quantity",
                        "content_uom",
                    }
                ),
                packaging_type_id=kind.id,
                code=" Manual ",
                name=" Manual name ",
                content_quantity=Decimal(24),
                content_uom="PCS",
            )
        )
        self.types.get_for_update.assert_awaited_once_with(kind.id)
        self.assertEqual(
            (
                result.packaging_type_id,
                result.code,
                result.name,
                result.content_quantity,
            ),
            (kind.id.uuid, "Manual", "Manual name", Decimal(24)),
        )
        self.assertEqual(result.id, self.identifier.uuid)

    async def test_noop_runs_domain_checks_and_skips_persistence(self) -> None:
        """Канонически одинаковое значение не записывается, активность всё равно проверяется."""
        result = await self.handler.execute(
            replace(
                self.command,
                fields=frozenset({"code", "content_quantity"}),
                code=" BOX-12 ",
                content_quantity=Decimal("12.000"),
            )
        )
        self.assertEqual(result.code, "BOX-12")
        self.items.save.assert_not_awaited()
        self.types.get_for_update.return_value = self.kind.deactivate()
        with self.assertRaises(InventoryItemConflictError):
            await self.handler.execute(replace(self.command, name="Ящик"))
        self.items.save.assert_not_awaited()

    async def test_missing_item_child_and_type_stop_without_persistence(self) -> None:
        """Упаковка проверяется внутри корня до чтения итогового типа."""
        with self.assertRaises(InventoryItemComponentNotFoundError):
            await self.handler.execute(
                replace(self.command, packaging_id=ItemPackagingIdVO(uuid4()))
            )
        self.types.get_for_update.assert_not_awaited()
        self.items.get_for_update.return_value = None
        with self.assertRaises(InventoryItemNotFoundError):
            await self.handler.execute(self.command)
        self.types.get_for_update.assert_not_awaited()
        self.items.get_for_update.return_value = self.item
        self.types.get_for_update.return_value = None
        with self.assertRaises(PackagingTypeNotFoundError):
            await self.handler.execute(self.command)
        self.items.save.assert_not_awaited()

    async def test_domain_rejects_duplicate_inactive_and_invalid_content(self) -> None:
        """Инварианты не дублируются в handler; любой отказ сохраняет исходный агрегат."""
        for field, value in [
            ("code", "OTHER"),
            ("code", " "),
            ("name", "\u200bName"),
            ("content_quantity", Decimal(0)),
            ("content_quantity", Decimal("-1")),
            ("content_quantity", Decimal("0.5")),
            ("content_uom", "KG"),
            ("content_uom", "UNKNOWN"),
        ]:
            with (
                self.subTest(field=field, value=value),
                self.assertRaises(InventoryError),
            ):
                await self.handler.execute(
                    replace(self.command, fields=frozenset({field}), **{field: value})
                )
        self.types.get_for_update.return_value = self.kind.deactivate()
        with self.assertRaises(InventoryItemConflictError):
            await self.handler.execute(self.command)
        self.items.save.assert_not_awaited()
