"""Локации, локальная активность и назначение основной STORAGE склада."""

import unittest
from dataclasses import FrozenInstanceError, replace
from uuid import uuid4

from src.modules.inventory.domain.policy.default_storage_location import (
    DefaultStorageLocationPolicy,
)
from src.modules.inventory.domain.policy.location_availability import (
    LocationAvailabilityPolicy,
)
from src.modules.inventory.domain.policy.location_placement import (
    LocationPlacementPolicy,
)
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    InvalidLocationCodeError,
    InvalidLocationHierarchyError,
    InvalidLocationNameError,
    InvalidStockLocationSnapshotError,
    InvalidStockLocationValueError,
    StockLocationInactiveError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import (
    DefaultStorageLocationInUseError,
    InvalidDefaultStorageLocationError,
    InvalidWarehouseSnapshotError,
    InvalidWarehouseValueError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class LocationValueObjectTests(unittest.TestCase):
    """Проверяет обязательные коды, названия и отдельную идентичность адресов."""

    def test_code_normalizes_case_and_name_preserves_case(self) -> None:
        """Коды сравниваются канонически, сохраняя ведущие нули; названия сохраняют регистр."""
        code = LocationCodeVO("  A-001  ")
        self.assertEqual(code.value, "a-001")
        self.assertEqual(code, LocationCodeVO("a-001"))
        self.assertEqual(len({code, LocationCodeVO("A-001")}), 1)
        self.assertEqual(LocationCodeVO("Straße"), LocationCodeVO("STRASSE"))
        self.assertEqual(LocationNameVO("  Стеллаж A  ").value, "Стеллаж A")
        self.assertNotEqual(LocationNameVO("MAIN"), LocationNameVO("main"))

    def test_text_values_reject_untyped_empty_and_control_values(self) -> None:
        """Сырые числа, пустота и управляющие символы отклоняются доменными ошибками."""
        for factory, error in (
            (LocationCodeVO, InvalidLocationCodeError),
            (LocationNameVO, InvalidLocationNameError),
        ):
            for value in (None, 1, True, "", "   ", "\tA", "A\n", "A\x7fB", "A\u200bB"):
                with (
                    self.subTest(factory=factory, value=value),
                    self.assertRaises(error),
                ):
                    factory(value)

    def test_location_identity_is_not_warehouse_identity(self) -> None:
        """Один UUID не делает идентификаторы склада и адреса взаимозаменяемыми."""
        value = uuid4()
        self.assertEqual(StockLocationIdVO(value).uuid, value)
        self.assertNotEqual(StockLocationIdVO(value), WarehouseIdVO(value))
        with self.assertRaises(EntityIdTypeError):
            StockLocationIdVO(str(value))


class StockLocationDomainTests(unittest.TestCase):
    """Проверяет создание, восстановление и межагрегатные инварианты по снимкам."""

    def setUp(self) -> None:
        """Готовит активный склад без основной локации и корневой адрес хранения."""
        self.warehouse = self.make_warehouse()
        self.location = self.make_location()

    def make_warehouse(self) -> Warehouse:
        """Создаёт независимую карточку склада с явным идентификатором."""
        return Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("MAIN"),
            name=WarehouseNameVO("Основной склад"),
        )

    def make_location(self, **changes: object) -> StockLocation:
        """Создаёт адрес через снимки с явно переопределёнными параметрами."""
        values = dict(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("A-001"),
            name=LocationNameVO("Стеллаж A"),
            location_type=LocationType.STORAGE,
            parent=None,
        )
        return StockLocation.create(**(values | changes))

    def restore_location(
        self, location: StockLocation | None = None, **changes: object
    ) -> StockLocation:
        """Восстанавливает полный состав без загрузки склада и родителя."""
        original = self.location if location is None else location
        values = dict(
            identifier=original.id,
            warehouse_id=original.warehouse_id,
            parent_location_id=original.parent_location_id,
            code=original.code,
            name=original.name,
            location_type=original.location_type,
            is_active=original.is_active,
        )
        return StockLocation.restore(**(values | changes))

    def restore_warehouse(
        self, warehouse: Warehouse | None = None, **changes: object
    ) -> Warehouse:
        """Восстанавливает карточку вместе с явно переданной основной локацией."""
        original = self.warehouse if warehouse is None else warehouse
        values = dict(
            identifier=original.id,
            code=original.code,
            name=original.name,
            is_active=original.is_active,
            default_storage_location_id=original.default_storage_location_id,
        )
        return Warehouse.restore(**(values | changes))

    def test_all_types_can_be_created_as_root_or_child_and_restored(self) -> None:
        """Назначение адреса не создаёт запасы; родитель задаётся только ссылкой."""
        for kind in LocationType:
            for parent in (None, self.location.snapshot()):
                with self.subTest(kind=kind, parent=parent):
                    location = self.make_location(location_type=kind, parent=parent)
                    self.assertTrue(location.is_active)
                    self.assertEqual(location.warehouse_id, self.warehouse.id)
                    self.assertEqual(
                        location.parent_location_id,
                        parent.id if parent is not None else None,
                    )
                    self.assertIs(location.location_type, kind)
                    restored = self.restore_location(location)
                    self.assertEqual(restored, location)
                    self.assertIs(restored.id, location.id)
                    self.assertIs(
                        restored.parent_location_id, location.parent_location_id
                    )
                    restored.ensure_available(warehouse=self.warehouse.snapshot())

    def test_creation_requires_active_warehouse_and_restore_does_not_load_it(
        self,
    ) -> None:
        """Историческая карточка восстанавливается независимо от текущей доступности склада."""
        blocked = self.warehouse.deactivate()
        with self.assertRaises(WarehouseInactiveError):
            self.make_location(warehouse=blocked.snapshot())
        restored = self.restore_location()
        with self.assertRaises(WarehouseInactiveError):
            restored.ensure_available(warehouse=blocked.snapshot())
        self.assertEqual(restored, self.location)

    def test_parent_must_belong_to_same_warehouse_and_cannot_be_self(self) -> None:
        """Чужой склад и прямая самоссылка отклоняются при создании и восстановлении."""
        foreign = self.make_location(warehouse=self.make_warehouse().snapshot())
        with self.assertRaises(StockLocationWarehouseMismatchError):
            self.make_location(parent=foreign.snapshot())
        with self.assertRaises(InvalidLocationHierarchyError):
            self.make_location(
                identifier=self.location.id, parent=self.location.snapshot()
            )
        with self.assertRaises(InvalidLocationHierarchyError):
            self.restore_location(parent_location_id=self.location.id)

    def test_rename_and_code_changes_preserve_fixed_location_dimensions(self) -> None:
        """Переименование сохраняет ID, склад, родителя, назначение и активность."""
        child = self.make_location(
            parent=self.location.snapshot(), location_type=LocationType.RECEIVING
        )
        changed = child.rename(LocationNameVO("Приёмка B")).change_code(
            LocationCodeVO(" B-002 ")
        )
        self.assertEqual(changed.code.value, "b-002")
        self.assertEqual(changed.name.value, "Приёмка B")
        self.assertEqual(
            (
                changed.id,
                changed.warehouse_id,
                changed.parent_location_id,
                changed.location_type,
                changed.is_active,
            ),
            (
                child.id,
                child.warehouse_id,
                child.parent_location_id,
                child.location_type,
                child.is_active,
            ),
        )
        self.assertEqual(child.code.value, "a-001")
        self.assertEqual(child.name.value, "Стеллаж A")

    def test_local_activity_is_idempotent_and_does_not_cascade(self) -> None:
        """Дети сохраняют локальную активность; неактивный родитель остаётся структурной ссылкой."""
        snapshot = self.warehouse.snapshot()
        child = self.make_location(parent=self.location.snapshot())
        blocked = self.location.deactivate(warehouse=snapshot)
        self.assertEqual(blocked.deactivate(warehouse=snapshot), blocked)
        self.assertEqual(blocked.activate(), self.location)
        self.assertEqual(self.location.activate(), self.location)
        child.ensure_available(warehouse=snapshot)
        another = self.make_location(parent=blocked.snapshot())
        another.ensure_available(warehouse=snapshot)
        self.assertTrue(self.location.is_active)
        self.assertFalse(blocked.is_active)

    def test_availability_requires_active_matching_warehouse_and_local_flag(
        self,
    ) -> None:
        """Состояние основной локации и родителей не подменяет локальную проверку двух флагов."""
        for active_warehouse in (True, False):
            warehouse = (
                self.warehouse if active_warehouse else self.warehouse.deactivate()
            )
            for active_location in (True, False):
                location = (
                    self.location
                    if active_location
                    else self.location.deactivate(warehouse=warehouse.snapshot())
                )
                with self.subTest(warehouse=active_warehouse, location=active_location):
                    if not active_warehouse:
                        with self.assertRaises(WarehouseInactiveError):
                            location.ensure_available(warehouse=warehouse.snapshot())
                    elif not active_location:
                        with self.assertRaises(StockLocationInactiveError):
                            location.ensure_available(warehouse=warehouse.snapshot())
                    else:
                        self.assertIsNone(
                            location.ensure_available(warehouse=warehouse.snapshot())
                        )
        foreign = self.make_warehouse().snapshot()
        with self.assertRaises(StockLocationWarehouseMismatchError):
            self.location.ensure_available(warehouse=foreign)
        with self.assertRaises(StockLocationWarehouseMismatchError):
            self.location.deactivate(warehouse=foreign)

    def test_factories_and_changes_require_typed_values(self) -> None:
        """Сырые коды, enum-строки и VO другого агрегата не преобразуются автоматически."""
        for factory in (self.make_location, self.restore_location):
            for changes in (
                dict(identifier=None),
                dict(identifier=self.warehouse.id),
                dict(code="A"),
                dict(code=WarehouseCodeVO("A")),
                dict(name=None),
                dict(name="Адрес"),
                dict(location_type="STORAGE"),
            ):
                with (
                    self.subTest(factory=factory, changes=changes),
                    self.assertRaises(InvalidStockLocationValueError),
                ):
                    factory(**changes)
        for changes in (
            dict(warehouse_id=self.location.id),
            dict(parent_location_id=self.warehouse.id),
            dict(is_active=1),
            dict(is_active=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockLocationValueError),
            ):
                self.restore_location(**changes)
        with self.assertRaises(InvalidStockLocationValueError):
            self.location.rename("Адрес")
        with self.assertRaises(InvalidStockLocationValueError):
            self.location.change_code(None)
        self.assertEqual(self.location.code, LocationCodeVO("A-001"))

    def test_every_warehouse_snapshot_consumer_rejects_malformed_contracts(
        self,
    ) -> None:
        """Снимок проверяется явно, включая тип основной локации и настоящий bool."""
        valid = self.warehouse.snapshot()
        for invalid in (
            None,
            self.warehouse,
            replace(valid, id=self.location.id),
            replace(valid, is_active=1),
            replace(valid, default_storage_location_id=self.warehouse.id),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidWarehouseSnapshotError):
                    self.make_location(warehouse=invalid)
                with self.assertRaises(InvalidWarehouseSnapshotError):
                    self.location.ensure_available(warehouse=invalid)
                with self.assertRaises(InvalidWarehouseSnapshotError):
                    self.location.deactivate(warehouse=invalid)
                with self.assertRaises(InvalidWarehouseSnapshotError):
                    DefaultStorageLocationPolicy.ensure_assignable(
                        location=self.location.snapshot(), warehouse=invalid
                    )

    def test_parent_snapshot_rejects_aggregate_and_untyped_fields(self) -> None:
        """Родитель передаётся проверяемым снимком вместо другого корня или сырых данных."""
        valid = self.location.snapshot()
        for invalid in (
            self.location,
            replace(valid, id=self.warehouse.id),
            replace(valid, warehouse_id=self.location.id),
            replace(valid, location_type="STORAGE"),
            replace(valid, is_active=1),
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidStockLocationSnapshotError),
            ):
                self.make_location(parent=invalid)

    def test_default_storage_assignment_preserves_warehouse_and_snapshots(self) -> None:
        """Назначение основной STORAGE создаёт новый склад, исходный остаётся без ссылки."""
        before = self.warehouse.snapshot()
        assigned = self.warehouse.set_default_storage_location(self.location.snapshot())
        self.assertIsNone(self.warehouse.default_storage_location_id)
        self.assertIsNone(before.default_storage_location_id)
        self.assertEqual(assigned.default_storage_location_id, self.location.id)
        self.assertEqual(
            (assigned.id, assigned.code, assigned.name, assigned.is_active),
            (
                self.warehouse.id,
                self.warehouse.code,
                self.warehouse.name,
                self.warehouse.is_active,
            ),
        )
        self.assertEqual(
            assigned.set_default_storage_location(self.location.snapshot()), assigned
        )
        self.assertEqual(self.restore_warehouse(assigned), assigned)
        self.assertEqual(
            assigned.rename(WarehouseNameVO("Другой")).default_storage_location_id,
            self.location.id,
        )
        self.assertEqual(
            assigned.change_code(WarehouseCodeVO("OTHER")).default_storage_location_id,
            self.location.id,
        )
        self.assertEqual(assigned.deactivate().activate(), assigned)
        self.warehouse.ensure_available()

    def test_default_assignment_requires_active_storage_of_same_warehouse(self) -> None:
        """Все остальные назначения и неактивная либо чужая локация отклоняются."""
        for kind in LocationType:
            location = self.make_location(location_type=kind)
            with self.subTest(kind=kind):
                if kind is LocationType.STORAGE:
                    assigned = self.warehouse.set_default_storage_location(
                        location.snapshot()
                    )
                    self.assertEqual(assigned.default_storage_location_id, location.id)
                else:
                    with self.assertRaises(InvalidDefaultStorageLocationError):
                        self.warehouse.set_default_storage_location(location.snapshot())
        with self.assertRaises(StockLocationInactiveError):
            self.warehouse.set_default_storage_location(
                self.location.deactivate(warehouse=self.warehouse.snapshot()).snapshot()
            )
        foreign = self.make_location(warehouse=self.make_warehouse().snapshot())
        with self.assertRaises(StockLocationWarehouseMismatchError):
            self.warehouse.set_default_storage_location(foreign.snapshot())
        self.assertIsNone(self.warehouse.default_storage_location_id)

    def test_default_location_cannot_be_deactivated_until_reassignment(self) -> None:
        """Защита действует и при заблокированном складе; переназначение освобождает старый адрес."""
        assigned = self.warehouse.set_default_storage_location(self.location.snapshot())
        for warehouse in (assigned, assigned.deactivate()):
            with (
                self.subTest(active=warehouse.is_active),
                self.assertRaises(DefaultStorageLocationInUseError),
            ):
                self.location.deactivate(warehouse=warehouse.snapshot())
        replacement = self.make_location(code=LocationCodeVO("B-001"))
        reassigned = assigned.set_default_storage_location(replacement.snapshot())
        blocked = self.location.deactivate(warehouse=reassigned.snapshot())
        self.assertFalse(blocked.is_active)
        self.assertTrue(self.location.is_active)
        with self.assertRaises(DefaultStorageLocationInUseError):
            replacement.deactivate(warehouse=reassigned.snapshot())
        self.assertEqual(assigned.default_storage_location_id, self.location.id)

    def test_default_can_be_configured_on_inactive_warehouse_without_unblocking_it(
        self,
    ) -> None:
        """Справочная настройка не изменяет административную активность склада."""
        blocked = self.warehouse.deactivate()
        assigned = blocked.set_default_storage_location(self.location.snapshot())
        self.assertFalse(assigned.is_active)
        self.assertEqual(assigned.default_storage_location_id, self.location.id)
        with self.assertRaises(WarehouseInactiveError):
            assigned.ensure_available()
        with self.assertRaises(WarehouseInactiveError):
            self.location.ensure_available(warehouse=assigned.snapshot())

    def test_default_consumers_reject_malformed_location_snapshots(self) -> None:
        """Оба контракта назначения и проверки доступности отклоняют повреждённые снимки."""
        valid = self.location.snapshot()
        for invalid in (
            None,
            self.location,
            replace(valid, id=self.warehouse.id),
            replace(valid, warehouse_id=self.location.id),
            replace(valid, location_type="STORAGE"),
            replace(valid, is_active=1),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidStockLocationSnapshotError):
                    self.warehouse.set_default_storage_location(invalid)
                with self.assertRaises(InvalidStockLocationSnapshotError):
                    LocationAvailabilityPolicy.ensure_available(
                        location=invalid, warehouse=self.warehouse.snapshot()
                    )
                with self.assertRaises(InvalidStockLocationSnapshotError):
                    DefaultStorageLocationPolicy.ensure_can_deactivate(
                        location=invalid, warehouse=self.warehouse.snapshot()
                    )

    def test_restore_warehouse_checks_reference_type_without_loading_location(
        self,
    ) -> None:
        """Историческая ссылка восстанавливается как ID; существование проверит срез хранения."""
        identifier = StockLocationIdVO(uuid4())
        restored = self.restore_warehouse(default_storage_location_id=identifier)
        self.assertIs(restored.default_storage_location_id, identifier)
        self.assertIs(restored.snapshot().default_storage_location_id, identifier)
        with self.assertRaises(InvalidWarehouseValueError):
            self.restore_warehouse(default_storage_location_id=self.warehouse.id)

    def test_roots_and_snapshots_are_immutable(self) -> None:
        """Нельзя менять идентичность, иерархию, тип или ссылки в обход методов."""
        for obj, field, value in (
            (self.location, "warehouse_id", self.make_warehouse().id),
            (self.location, "parent_location_id", StockLocationIdVO(uuid4())),
            (self.location, "location_type", LocationType.TRANSIT),
            (self.location, "is_active", False),
            (self.location.code, "value", "other"),
            (self.location.name, "value", "Другой"),
            (self.location.snapshot(), "is_active", False),
            (self.warehouse, "default_storage_location_id", self.location.id),
            (
                self.warehouse.snapshot(),
                "default_storage_location_id",
                self.location.id,
            ),
        ):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)

    def test_invalid_direct_states_cannot_bypass_domain_checks(self) -> None:
        """Публичные методы проверяют собственное состояние и прямую самоссылку."""
        invalid = StockLocation(
            self.location.id,
            self.warehouse.id,
            None,
            self.location.code,
            self.location.name,
            "STORAGE",
            True,
        )
        with self.assertRaises(InvalidStockLocationValueError):
            invalid.ensure_available(warehouse=self.warehouse.snapshot())
        with self.assertRaises(InvalidStockLocationValueError):
            invalid.deactivate(warehouse=self.warehouse.snapshot())
        with self.assertRaises(InvalidStockLocationValueError):
            LocationPlacementPolicy.ensure_allowed(
                location_id=self.warehouse.id, warehouse=self.warehouse.snapshot()
            )
