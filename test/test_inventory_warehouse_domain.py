"""Карточка склада, канонический код и административная активность."""

import unittest
from dataclasses import FrozenInstanceError
from uuid import uuid4

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseCodeError,
    InvalidWarehouseNameError,
    InvalidWarehouseValueError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class WarehouseValueObjectTests(unittest.TestCase):
    """Проверяет обязательные текстовые значения и отдельный тип идентичности склада."""

    def test_code_uses_trim_casefold_and_numeric_characters_preserve_zeros(
        self,
    ) -> None:
        """MAIN и main равны, а ведущие нули и внутренние символы сохраняются."""
        code = WarehouseCodeVO("  MAIN-001  ")
        self.assertEqual(code.value, "main-001")
        self.assertEqual(code, WarehouseCodeVO("main-001"))
        self.assertEqual(len({code, WarehouseCodeVO("Main-001")}), 1)
        self.assertEqual(WarehouseCodeVO(" Straße "), WarehouseCodeVO("STRASSE"))

    def test_name_trims_and_preserves_case(self) -> None:
        """Название остаётся пользовательским текстом с исходным регистром."""
        self.assertEqual(WarehouseNameVO("  Основной склад  ").value, "Основной склад")
        self.assertNotEqual(WarehouseNameVO("MAIN"), WarehouseNameVO("main"))

    def test_text_values_reject_empty_untyped_and_control_input(self) -> None:
        """Оба VO отклоняют пустоту и управляющие символы до нормализации."""
        for factory, error in (
            (WarehouseCodeVO, InvalidWarehouseCodeError),
            (WarehouseNameVO, InvalidWarehouseNameError),
        ):
            for value in (
                None,
                123,
                True,
                "",
                "   ",
                "\tMAIN",
                "MAIN\n",
                "MA\x7fIN",
                "MA\u200bIN",
            ):
                with (
                    self.subTest(factory=factory, value=value),
                    self.assertRaises(error),
                ):
                    factory(value)

    def test_identifier_requires_uuid_and_is_not_an_inventory_item_id(self) -> None:
        """Идентификаторы разных агрегатов не взаимозаменяемы даже при одном UUID."""
        value = uuid4()
        self.assertEqual(WarehouseIdVO(value).uuid, value)
        self.assertNotEqual(WarehouseIdVO(value), InventoryItemIdVO(value))
        with self.assertRaises(EntityIdTypeError):
            WarehouseIdVO(str(value))


class WarehouseDomainTests(unittest.TestCase):
    """Проверяет фабрики и переходы через публичные методы корня склада."""

    def setUp(self) -> None:
        """Готовит активный склад с явно заданной идентичностью."""
        self.warehouse = self.create_warehouse()

    def create_warehouse(self, **changes: object) -> Warehouse:
        """Создаёт корректную карточку с явно переопределёнными значениями."""
        values = dict(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("MAIN"),
            name=WarehouseNameVO("Основной склад"),
        )
        return Warehouse.create(**(values | changes))

    def restore_warehouse(self, **changes: object) -> Warehouse:
        """Восстанавливает полный собственный состав и административную активность."""
        values = dict(
            identifier=self.warehouse.id,
            code=self.warehouse.code,
            name=self.warehouse.name,
            is_active=self.warehouse.is_active,
            default_storage_location_id=self.warehouse.default_storage_location_id,
        )
        return Warehouse.restore(**(values | changes))

    def test_create_produces_active_available_card_with_canonical_code(self) -> None:
        """Новая карточка активна и использует каноническое значение кода."""
        self.assertTrue(self.warehouse.is_active)
        self.assertEqual(self.warehouse.code.value, "main")
        self.assertIsNone(self.warehouse.ensure_available())

    def test_restore_preserves_identity_and_both_activity_states(self) -> None:
        """Восстановление не создаёт новые ID и не активирует заблокированный склад."""
        self.assertEqual(self.restore_warehouse(), self.warehouse)
        for active in (True, False):
            with self.subTest(active=active):
                restored = self.restore_warehouse(is_active=active)
                self.assertIs(restored.id, self.warehouse.id)
                self.assertIs(restored.code, self.warehouse.code)
                self.assertIs(restored.name, self.warehouse.name)
                self.assertIs(restored.is_active, active)
                if active:
                    restored.ensure_available()
                else:
                    with self.assertRaises(WarehouseInactiveError):
                        restored.ensure_available()

    def test_rename_and_code_change_preserve_original_and_identity(self) -> None:
        """Изменение справочных данных разрешено и для неактивной карточки."""
        for warehouse in (self.warehouse, self.warehouse.deactivate()):
            with self.subTest(active=warehouse.is_active):
                renamed = warehouse.rename(WarehouseNameVO("Резервный склад"))
                changed = renamed.change_code(WarehouseCodeVO(" BACKUP "))
                self.assertEqual(changed.name.value, "Резервный склад")
                self.assertEqual(changed.code.value, "backup")
                self.assertIs(changed.id, warehouse.id)
                self.assertIs(changed.is_active, warehouse.is_active)
                self.assertEqual(warehouse.code.value, "main")
                self.assertEqual(warehouse.name.value, "Основной склад")
                self.assertEqual(
                    warehouse.change_code(WarehouseCodeVO(" MaIn ")), warehouse
                )

    def test_activity_transitions_are_idempotent_and_do_not_mutate_original(
        self,
    ) -> None:
        """Повторные переключения допустимы, а доступность следует за текущим экземпляром."""
        blocked = self.warehouse.deactivate()
        self.assertFalse(blocked.is_active)
        self.assertEqual(blocked.deactivate(), blocked)
        with self.assertRaises(WarehouseInactiveError):
            blocked.ensure_available()
        active = blocked.activate()
        self.assertEqual(active, self.warehouse)
        self.assertEqual(active.activate(), active)
        self.assertIs(active.id, blocked.id)
        active.ensure_available()
        self.warehouse.ensure_available()
        self.assertFalse(blocked.is_active)

    def test_factories_require_typed_state_and_restore_requires_real_bool(self) -> None:
        """Сырые значения и VO другого назначения не проходят границу агрегата."""
        for factory in (self.create_warehouse, self.restore_warehouse):
            for changes in (
                dict(identifier=None),
                dict(identifier=InventoryItemIdVO(uuid4())),
                dict(code=None),
                dict(code="MAIN"),
                dict(code=WarehouseNameVO("MAIN")),
                dict(name=None),
                dict(name="Основной"),
                dict(name=WarehouseCodeVO("MAIN")),
            ):
                with (
                    self.subTest(factory=factory, changes=changes),
                    self.assertRaises(InvalidWarehouseValueError),
                ):
                    factory(**changes)
        for active in (None, 0, 1, "true"):
            with (
                self.subTest(active=active),
                self.assertRaises(InvalidWarehouseValueError),
            ):
                self.restore_warehouse(is_active=active)

    def test_failed_changes_preserve_original_state(self) -> None:
        """Неверные параметры методов не меняют код, название или активность."""
        for value in (None, "MAIN", WarehouseNameVO("MAIN")):
            with (
                self.subTest(code=value),
                self.assertRaises(InvalidWarehouseValueError),
            ):
                self.warehouse.change_code(value)
        for value in (None, "MAIN", WarehouseCodeVO("MAIN")):
            with (
                self.subTest(name=value),
                self.assertRaises(InvalidWarehouseValueError),
            ):
                self.warehouse.rename(value)
        self.assertEqual(self.warehouse.code, WarehouseCodeVO("MAIN"))
        self.assertEqual(self.warehouse.name, WarehouseNameVO("Основной склад"))
        self.assertTrue(self.warehouse.is_active)

    def test_direct_invalid_state_cannot_bypass_availability_check(self) -> None:
        """Проверка доступности отклоняет сырое состояние вместо интерпретации его как bool."""
        invalid = Warehouse(
            self.warehouse.id, self.warehouse.code, self.warehouse.name, 1, None
        )
        with self.assertRaises(InvalidWarehouseValueError):
            invalid.ensure_available()

    def test_root_and_value_objects_are_immutable(self) -> None:
        """Корень и его значения нельзя менять в обход доменных методов."""
        for obj, field, value in (
            (self.warehouse, "id", WarehouseIdVO(uuid4())),
            (self.warehouse, "code", WarehouseCodeVO("OTHER")),
            (self.warehouse, "name", WarehouseNameVO("Другой")),
            (self.warehouse, "is_active", False),
            (self.warehouse.code, "value", "other"),
            (self.warehouse.name, "value", "Другой"),
        ):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)
