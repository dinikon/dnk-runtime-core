"""Плановые строки, подтверждение и отмена складского документа без физических движений."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    InvalidQuantityConversionError,
    QuantityConversionMismatchError,
    QuantityStepError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
    InvalidInventoryItemValueError,
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_document_confirmation import (
    StockDocumentConfirmationPolicy,
)
from src.modules.inventory.domain.policy.stock_document_line import (
    StockDocumentLinePolicy,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidDocumentSourceError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentLineError,
    InvalidStockDocumentValueError,
    StockDocumentItemMismatchError,
    StockDocumentLineConflictError,
    StockDocumentLineNotFoundError,
    StockDocumentNotDraftError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockDocumentDomainTests(unittest.TestCase):
    """Проверяет планирование через реальные товары и склады и явные снимки настроек."""

    def setUp(self) -> None:
        """Готовит товар с шагом 0.05 кг, активный склад, владельца и пустой черновик."""
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("GRAIN"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("MAIN"),
            name=WarehouseNameVO("Основной склад"),
        )
        self.owner_id = StockOwnerIdVO(uuid4())
        self.time = datetime(2026, 11, 3, 9, tzinfo=UTC)
        self.document = self.create()
        self.line = self.create_line()
        self.planned = self.document.add_line(
            self.line,
            inventory_item=self.item.document_snapshot(),
            updated_at=self.at(1),
        )

    def at(self, minute: int) -> datetime:
        """Возвращает явное время сценария без системных часов."""
        return self.time + timedelta(minutes=minute)

    def create(self, **changes: object) -> StockDocument:
        """Создаёт пустой черновик с явно переопределяемыми реквизитами."""
        return StockDocument.create(
            **(
                dict(
                    identifier=StockDocumentIdVO(uuid4()),
                    operation_type=StockOperationType.RECEIPT,
                    warehouse=self.warehouse.snapshot(),
                    owner_id=self.owner_id,
                    created_at=self.time,
                )
                | changes
            )
        )

    def create_line(
        self, item: InventoryItem | None = None, **changes: object
    ) -> StockDocumentLine:
        """Создаёт план пяти килограммов, введённый в граммах."""
        value = self.item if item is None else item
        return StockDocumentLine.create(
            **(
                dict(
                    identifier=StockDocumentLineIdVO(uuid4()),
                    inventory_item=value.document_snapshot(),
                    quantity=QuantityVO(Decimal(5000)),
                    uom=UomCodeVO("G"),
                )
                | changes
            )
        )

    def restore_line(
        self, reference: StockDocumentLine | None = None, **changes: object
    ) -> StockDocumentLine:
        """Восстанавливает полный собственный состав плановой строки."""
        line = self.line if reference is None else reference
        return StockDocumentLine.restore(
            **(
                dict(
                    identifier=line.id,
                    inventory_item_id=line.inventory_item_id,
                    sku=line.sku,
                    base_uom=line.base_uom,
                    planned_qty=line.planned_qty,
                    conversion=line.conversion,
                    executed_qty=line.executed_qty,
                )
                | changes
            )
        )

    def restore(
        self, reference: StockDocument | None = None, **changes: object
    ) -> StockDocument:
        """Восстанавливает документ без снимков актуальных товаров и склада."""
        document = self.planned if reference is None else reference
        return StockDocument.restore(
            **(
                dict(
                    identifier=document.id,
                    operation_type=document.operation_type,
                    warehouse_id=document.warehouse_id,
                    owner_id=document.owner_id,
                    source=document.source,
                    status=document.status,
                    lines=document.lines,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    version=document.version,
                )
                | changes
            )
        )

    def change(
        self, reference: StockDocument | None = None, **changes: object
    ) -> StockDocument:
        """Меняет количество существующей строки черновика на 7.5 кг."""
        document = self.planned if reference is None else reference
        return document.change_line(
            **(
                dict(
                    identifier=self.line.id,
                    quantity=QuantityVO(Decimal(7500)),
                    uom=UomCodeVO("G"),
                    inventory_item=self.item.document_snapshot(),
                    updated_at=self.at(2),
                )
                | changes
            )
        )

    def confirm(
        self, reference: StockDocument | None = None, **changes: object
    ) -> StockDocument:
        """Подтверждает план по текущему складу и ровно нужным снимкам товаров."""
        document = self.planned if reference is None else reference
        return document.confirm(
            **(
                dict(
                    warehouse=self.warehouse.snapshot(),
                    inventory_items=(self.item.document_snapshot(),),
                    updated_at=self.at(3),
                )
                | changes
            )
        )

    def test_create_is_empty_draft_version_zero_with_explicit_owner_and_time(
        self,
    ) -> None:
        """Создаёт самостоятельный план с обязательными реквизитами без номеров и физического остатка."""
        for kind in StockOperationType:
            document = self.create(operation_type=kind)
            self.assertEqual(document.status, StockDocumentStatus.DRAFT)
            self.assertEqual(document.lines, ())
            self.assertEqual(document.version, 0)
            self.assertEqual(document.owner_id, self.owner_id)
            self.assertEqual(document.warehouse_id, self.warehouse.id)
            self.assertIsNone(document.source)
            self.assertEqual(document.created_at, self.time)
            self.assertEqual(document.updated_at, self.time)
        self.assertEqual(
            {status.value for status in StockDocumentStatus},
            {"DRAFT", "CONFIRMED", "PARTIALLY_EXECUTED", "COMPLETED", "CANCELLED"},
        )

    def test_source_normalizes_spaces_preserves_case_and_is_immutable(self) -> None:
        """Ссылка на внешнее основание не превращается в SKU и не проверяет другую систему."""
        source = DocumentSourceVO(" Sales ", " Order-ABC-001 ")
        document = self.create(source=source)
        self.assertEqual((source.system, source.reference), ("Sales", "Order-ABC-001"))
        self.assertIs(document.source, source)
        self.assertIs(self.restore(document).source, source)
        with self.assertRaises(FrozenInstanceError):
            source.reference = "Other"
        for field in ("system", "reference"):
            for value in (None, 1, True, "", "   ", "A\nB", "A\u200bB"):
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(InvalidDocumentSourceError),
                ):
                    DocumentSourceVO(
                        **(dict(system="Sales", reference="001") | {field: value})
                    )

    def test_item_document_snapshot_is_minimal_typed_and_validates_origin(self) -> None:
        """Геттер не раскрывает упаковки, штрихкоды и сроки; повторно проверяет исходный товар."""
        snapshot = self.item.document_snapshot()
        self.assertEqual(
            set(snapshot.__dataclass_fields__),
            {"inventory_item_id", "sku", "base_uom", "quantity_rules", "tracking_mode"},
        )
        self.assertIs(snapshot.inventory_item_id, self.item.id)
        self.assertIs(snapshot.sku, self.item.sku)
        snapshot.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            snapshot.sku = SkuVO("OTHER")
        with self.assertRaises(InvalidInventoryItemValueError):
            replace(self.item, sku="RAW").document_snapshot()
        for changes in (
            dict(inventory_item_id=uuid4()),
            dict(sku="RAW"),
            dict(base_uom="KG"),
            dict(quantity_rules=None),
            dict(tracking_mode="LOT"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidInventoryItemDocumentSnapshotError),
            ):
                replace(snapshot, **changes).ensure_valid()
        with self.assertRaises(UnknownUomError):
            replace(snapshot, base_uom=UomCodeVO("BOX")).ensure_valid()

    def test_line_derives_base_quantity_and_preserves_original_input(self) -> None:
        """Фиксирует исходные 5000 G и коэффициент 0.001 как положительный план 5 KG."""
        self.assertEqual(self.line.planned_qty.value, Decimal(5))
        self.assertEqual(self.line.base_uom, UomCodeVO("KG"))
        self.assertEqual(self.line.conversion.quantity.value, Decimal(5000))
        self.assertEqual(self.line.conversion.uom, UomCodeVO("G"))
        self.assertEqual(self.line.conversion.factor_to_base, Decimal("0.001"))
        self.assertEqual(self.line.sku, SkuVO("GRAIN"))
        for kind in StockOperationType:
            document = self.create(operation_type=kind).add_line(
                self.line,
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(1),
            )
            self.assertEqual(document.lines[0].planned_qty.value, Decimal(5))

    def test_quantities_for_all_dimensions_are_converted_and_validated(self) -> None:
        """Планирует штуки, жидкость, вес, площадь и длину общими единицами без особых документов."""
        for base, step, quantity, uom, expected in (
            ("PCS", "1", "12", "PCS", "12"),
            ("L", "0.001", "1250", "ML", "1.25"),
            ("KG", "0.05", "1250", "G", "1.25"),
            ("M2", "0.01", "25000", "CM2", "2.5"),
            ("M", "0.1", "250", "CM", "2.5"),
        ):
            item = InventoryItem.create(
                identifier=InventoryItemIdVO(uuid4()),
                sku=SkuVO(base),
                base_uom=UomCodeVO(base),
                quantity_rules=QuantityRulesVO(Decimal(step)),
            )
            with self.subTest(base=base):
                line = self.create_line(
                    item, quantity=QuantityVO(Decimal(quantity)), uom=UomCodeVO(uom)
                )
                self.assertEqual(line.planned_qty.value, Decimal(expected))

    def test_line_rejects_zero_wrong_dimension_and_nonmultiple_of_step(self) -> None:
        """Нулевой план, литры вместо килограммов и некратное количество не проходят создание."""
        for changes, error in (
            (dict(quantity=QuantityVO(Decimal(0))), InvalidQuantityConversionError),
            (dict(quantity=QuantityVO(Decimal(1230))), QuantityStepError),
            (dict(uom=UomCodeVO("L")), IncompatibleUomError),
            (dict(inventory_item=self.item), InvalidInventoryItemDocumentSnapshotError),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                self.create_line(**changes)

    def test_serial_plans_are_whole_counts_without_serial_cards(self) -> None:
        """Серийный план на 12 экземпляров не требует заранее выбрать их идентификаторы."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = InventoryItem.create(
                identifier=InventoryItemIdVO(uuid4()),
                sku=SkuVO("SERIAL"),
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
                expiration_mode=ExpirationMode.REQUIRED,
            )
            line = self.create_line(
                item, quantity=QuantityVO(Decimal(12)), uom=UomCodeVO("PCS")
            )
            document = self.document.add_line(
                line, inventory_item=item.document_snapshot(), updated_at=self.at(1)
            )
            confirmed = self.confirm(
                document, inventory_items=(item.document_snapshot(),)
            )
            self.assertEqual(confirmed.lines[0].planned_qty.value, Decimal(12))
            for quantity in ("0.5", "12.01"):
                with (
                    self.subTest(mode=mode, quantity=quantity),
                    self.assertRaises(QuantityStepError),
                ):
                    self.create_line(
                        item,
                        quantity=QuantityVO(Decimal(quantity)),
                        uom=UomCodeVO("PCS"),
                    )
            for changes in (
                dict(base_uom=UomCodeVO("KG")),
                dict(quantity_rules=QuantityRulesVO(Decimal(2))),
            ):
                with (
                    self.subTest(changes=changes),
                    self.assertRaises(InvalidTrackingConfigurationError),
                ):
                    replace(item.document_snapshot(), **changes).ensure_valid()

    def test_lot_and_expiration_are_not_selected_at_planning(self) -> None:
        """Подтверждает план приёмки LOT/REQUIRED до появления карточки конкретной партии."""
        item = replace(
            self.item,
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        document = self.document.add_line(
            self.create_line(item),
            inventory_item=item.document_snapshot(),
            updated_at=self.at(1),
        )
        confirmed = self.confirm(document, inventory_items=(item.document_snapshot(),))
        self.assertEqual(confirmed.status, StockDocumentStatus.CONFIRMED)
        self.assertEqual(
            set(confirmed.lines[0].__dataclass_fields__),
            {
                "id",
                "inventory_item_id",
                "sku",
                "base_uom",
                "planned_qty",
                "conversion",
                "executed_qty",
            },
        )

    def test_add_change_remove_preserve_identity_and_increment_versions(self) -> None:
        """Изменения состава возвращают новые документы и не переписывают исходные объекты."""
        changed = self.change()
        removed = changed.remove_line(self.line.id, updated_at=self.at(3))
        self.assertEqual(
            (
                self.document.version,
                self.planned.version,
                changed.version,
                removed.version,
            ),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            (
                len(self.document.lines),
                len(self.planned.lines),
                len(changed.lines),
                len(removed.lines),
            ),
            (0, 1, 1, 0),
        )
        self.assertEqual(changed.lines[0].planned_qty.value, Decimal("7.5"))
        self.assertEqual(self.planned.lines[0].planned_qty.value, Decimal(5))
        self.assertEqual(changed.lines[0].id, self.line.id)
        self.assertEqual(changed.id, self.document.id)
        self.assertEqual(changed.created_at, self.document.created_at)
        self.assertEqual(changed.updated_at, self.at(2))
        self.assertEqual(removed.status, StockDocumentStatus.DRAFT)

    def test_duplicate_line_ids_rejected_but_same_item_may_repeat(self) -> None:
        """Не объединяет строки одного товара и не разрешает повторный ID дочерней Entity."""
        second = self.create_line()
        document = self.planned.add_line(
            second, inventory_item=self.item.document_snapshot(), updated_at=self.at(2)
        )
        self.assertEqual(len(document.lines), 2)
        self.assertEqual(
            document.lines[0].inventory_item_id, document.lines[1].inventory_item_id
        )
        self.assertEqual(self.confirm(document).status, StockDocumentStatus.CONFIRMED)
        with self.assertRaises(StockDocumentLineConflictError):
            self.planned.add_line(
                self.line,
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(2),
            )
        with self.assertRaises(StockDocumentLineConflictError):
            self.restore(lines=(self.line, self.line))

    def test_get_change_and_remove_require_existing_typed_line(self) -> None:
        """Строка ищется только внутри своего документа, без самостоятельного репозитория."""
        self.assertIs(self.planned.get_line(self.line.id), self.line)
        for identifier, error in (
            (StockDocumentLineIdVO(uuid4()), StockDocumentLineNotFoundError),
            (uuid4(), InvalidStockDocumentLineError),
        ):
            with self.subTest(identifier=identifier):
                with self.assertRaises(error):
                    self.planned.get_line(identifier)
                with self.assertRaises(error):
                    self.change(identifier=identifier)
                with self.assertRaises(error):
                    self.planned.remove_line(identifier, updated_at=self.at(2))

    def test_confirm_requires_nonempty_document_and_locks_plan(self) -> None:
        """Подтверждённый план сохраняет строки и версию, но не допускает повторных переходов."""
        with self.assertRaises(EmptyStockDocumentError):
            self.confirm(self.document, inventory_items=())
        confirmed = self.confirm()
        self.assertEqual(confirmed.status, StockDocumentStatus.CONFIRMED)
        self.assertEqual(confirmed.version, 2)
        self.assertEqual(confirmed.updated_at, self.at(3))
        self.assertIs(confirmed.lines, self.planned.lines)
        self.assertEqual(self.planned.status, StockDocumentStatus.DRAFT)
        for action in (
            lambda: confirmed.add_line(
                self.create_line(),
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(4),
            ),
            lambda: self.change(confirmed, updated_at=self.at(4)),
            lambda: confirmed.remove_line(self.line.id, updated_at=self.at(4)),
            lambda: self.confirm(confirmed, updated_at=self.at(4)),
        ):
            with self.assertRaises(StockDocumentNotDraftError):
                action()

    def test_cancel_only_draft_preserves_lines_and_blocks_future_changes(self) -> None:
        """Отменить можно пустой или заполненный черновик без удаления его истории."""
        for original in (self.document, self.planned):
            cancelled = original.cancel(updated_at=self.at(3))
            self.assertEqual(cancelled.status, StockDocumentStatus.CANCELLED)
            self.assertEqual(cancelled.version, original.version + 1)
            self.assertIs(cancelled.lines, original.lines)
            for action in (
                lambda: self.confirm(cancelled),
                lambda: cancelled.cancel(updated_at=self.at(4)),
                lambda: cancelled.add_line(
                    self.create_line(),
                    inventory_item=self.item.document_snapshot(),
                    updated_at=self.at(4),
                ),
                lambda: self.change(cancelled),
                lambda: cancelled.remove_line(self.line.id, updated_at=self.at(4)),
            ):
                with self.assertRaises(StockDocumentNotDraftError):
                    action()

    def test_confirmation_requires_same_active_warehouse(self) -> None:
        """Не подтверждает план по другому складу или после административного отключения склада."""
        inactive = self.warehouse.deactivate().snapshot()
        for warehouse, error in (
            (inactive, WarehouseInactiveError),
            (
                replace(self.warehouse.snapshot(), id=WarehouseIdVO(uuid4())),
                InvalidStockDocumentContextError,
            ),
            (self.warehouse, InvalidWarehouseSnapshotError),
            (
                replace(self.warehouse.snapshot(), is_active=1),
                InvalidWarehouseSnapshotError,
            ),
        ):
            with self.subTest(warehouse=warehouse), self.assertRaises(error):
                self.confirm(warehouse=warehouse)
        with self.assertRaises(WarehouseInactiveError):
            self.create(warehouse=inactive)
        self.assertEqual(
            self.planned.cancel(updated_at=self.at(3)).status,
            StockDocumentStatus.CANCELLED,
        )

    def test_confirmation_requires_exact_set_of_unique_item_snapshots(self) -> None:
        """Повторяющиеся строки используют один снимок товара; отсутствующие и лишние снимки запрещены."""
        other = replace(self.item, id=InventoryItemIdVO(uuid4()))
        for snapshots in (
            (),
            [self.item.document_snapshot()],
            (other.document_snapshot(),),
            (self.item.document_snapshot(), other.document_snapshot()),
            (self.item.document_snapshot(), self.item.document_snapshot()),
        ):
            with (
                self.subTest(snapshots=snapshots),
                self.assertRaises(InvalidStockDocumentContextError),
            ):
                self.confirm(inventory_items=snapshots)
        with self.assertRaises(InvalidInventoryItemDocumentSnapshotError):
            self.confirm(inventory_items=(self.item,))
        document = self.planned.add_line(
            self.create_line(other),
            inventory_item=other.document_snapshot(),
            updated_at=self.at(2),
        )
        confirmed = self.confirm(
            document,
            inventory_items=(other.document_snapshot(), self.item.document_snapshot()),
        )
        self.assertEqual(len(confirmed.lines), 2)

    def test_wrong_item_snapshot_is_rejected_when_adding_or_changing(self) -> None:
        """Не привязывает чужие настройки к строке с прежним идентификатором товара."""
        other = replace(self.item, id=InventoryItemIdVO(uuid4())).document_snapshot()
        with self.assertRaises(StockDocumentItemMismatchError):
            self.document.add_line(
                self.line, inventory_item=other, updated_at=self.at(1)
            )
        with self.assertRaises(StockDocumentItemMismatchError):
            self.change(inventory_item=other)
        with self.assertRaises(InvalidStockDocumentLineError):
            self.document.add_line(
                None,
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(1),
            )

    def test_base_unit_cannot_be_reinterpreted_at_add_change_or_confirm(self) -> None:
        """Смена KG на G у товара не превращает старый план 5 кг в 5 граммов."""
        current = replace(self.item.document_snapshot(), base_uom=UomCodeVO("G"))
        with self.assertRaises(StockDocumentUomMismatchError):
            self.document.add_line(
                self.line, inventory_item=current, updated_at=self.at(1)
            )
        with self.assertRaises(StockDocumentUomMismatchError):
            self.change(inventory_item=current)
        with self.assertRaises(StockDocumentUomMismatchError):
            self.confirm(inventory_items=(current,))

    def test_current_step_revalidated_and_legacy_quantity_can_be_fixed_in_draft(
        self,
    ) -> None:
        """Ужесточение шага требует исправить план, но не блокирует само редактирование черновика."""
        current = replace(
            self.item.document_snapshot(), quantity_rules=QuantityRulesVO(Decimal(2))
        )
        with self.assertRaises(QuantityStepError):
            self.confirm(inventory_items=(current,))
        fixed = self.change(quantity=QuantityVO(Decimal(6000)), inventory_item=current)
        self.assertEqual(fixed.lines[0].planned_qty.value, Decimal(6))
        self.assertEqual(
            self.confirm(fixed, inventory_items=(current,)).status,
            StockDocumentStatus.CONFIRMED,
        )
        with self.assertRaises(QuantityStepError):
            self.change(quantity=QuantityVO(Decimal(1230)))

    def test_item_rename_does_not_rewrite_historical_sku(self) -> None:
        """Изменение и подтверждение сохраняют исходный SKU, а новая строка получает текущий."""
        renamed = self.item.change_sku(SkuVO("NEW-SKU"))
        changed = self.change(inventory_item=renamed.document_snapshot())
        confirmed = self.confirm(
            changed, inventory_items=(renamed.document_snapshot(),)
        )
        self.assertEqual(confirmed.lines[0].sku, SkuVO("GRAIN"))
        self.assertEqual(self.create_line(renamed).sku, SkuVO("NEW-SKU"))
        self.assertEqual(self.item.sku, SkuVO("GRAIN"))

    def test_noop_preserves_instance_version_time_and_recorded_decimal_format(
        self,
    ) -> None:
        """Численно равный ввод с конечными нулями не создаёт фиктивного изменения документа."""
        unchanged = self.change(
            quantity=QuantityVO(Decimal("5000.000")), updated_at=self.at(2)
        )
        self.assertIs(unchanged, self.planned)
        self.assertEqual(unchanged.version, 1)
        self.assertEqual(unchanged.updated_at, self.at(1))
        self.assertEqual(
            unchanged.lines[0].conversion.quantity.value.as_tuple(),
            Decimal(5000).as_tuple(),
        )
        changed_input = self.change(
            quantity=QuantityVO(Decimal(5)), uom=UomCodeVO("KG")
        )
        self.assertEqual(changed_input.lines[0].planned_qty.value, Decimal(5))
        self.assertEqual(changed_input.version, 2)
        self.assertEqual(changed_input.lines[0].conversion.uom, UomCodeVO("KG"))

    def test_time_normalization_and_monotonic_history(self) -> None:
        """Нормализует смещение в UTC и запрещает изменение задним числом даже при no-op."""
        local = datetime(2026, 11, 3, 11, tzinfo=timezone(timedelta(hours=2)))
        document = self.create(created_at=local)
        self.assertEqual(document.created_at, self.time)
        self.assertIs(document.created_at.tzinfo, UTC)
        changed = self.change(
            updated_at=datetime(2026, 11, 3, 11, 2, tzinfo=timezone(timedelta(hours=2)))
        )
        self.assertEqual(changed.updated_at, self.at(2))
        for value in (
            None,
            self.time.date(),
            datetime(2026, 11, 3),
            "2026-11-03",
            datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        ):
            with self.subTest(value=value), self.assertRaises(StockDocumentTimeError):
                self.create(created_at=value)
        for action in (
            lambda: self.change(updated_at=self.time),
            lambda: self.change(
                quantity=QuantityVO(Decimal(5000)), updated_at=self.time
            ),
            lambda: self.confirm(updated_at=self.time),
            lambda: self.planned.cancel(updated_at=self.time),
            lambda: self.planned.remove_line(self.line.id, updated_at=self.time),
        ):
            with self.assertRaises(StockDocumentTimeError):
                action()
        self.assertEqual(self.change(updated_at=self.at(1)).updated_at, self.at(1))

    def test_restore_preserves_all_states_without_current_snapshots(self) -> None:
        """Восстанавливает черновик, подтверждение и отмену без получения внешних данных."""
        source = DocumentSourceVO("Sales", "order-001")
        originals = (
            self.document,
            self.planned,
            self.confirm(),
            self.planned.cancel(updated_at=self.at(3)),
        )
        for original in originals:
            restored = self.restore(original, source=source)
            self.assertEqual(restored.status, original.status)
            self.assertEqual(restored.version, original.version)
            self.assertIs(restored.id, original.id)
            self.assertIs(restored.lines, original.lines)
            self.assertIs(restored.source, source)
            self.assertEqual(restored.owner_id, original.owner_id)
            self.assertEqual(restored.created_at, original.created_at)
            self.assertEqual(restored.updated_at, original.updated_at)

    def test_restore_validates_own_types_status_version_lines_and_chronology(
        self,
    ) -> None:
        """Не принимает сырые типы, bool-версию, повтор строк и невозможное собственное состояние."""
        for changes in (
            dict(identifier=uuid4()),
            dict(operation_type="RECEIPT"),
            dict(warehouse_id=uuid4()),
            dict(owner_id=None),
            dict(source="manual"),
            dict(status="DRAFT"),
            dict(lines=[self.line]),
            dict(version=True),
            dict(version=-1),
            dict(version=Decimal(1)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDocumentValueError),
            ):
                self.restore(**changes)
        with self.assertRaises(InvalidStockDocumentLineError):
            self.restore(lines=(None,))
        with self.assertRaises(EmptyStockDocumentError):
            self.restore(status=StockDocumentStatus.CONFIRMED, lines=())
        with self.assertRaises(StockDocumentTimeError):
            self.restore(updated_at=self.time - timedelta(seconds=1))
        for identifier_type in (StockDocumentIdVO, StockDocumentLineIdVO):
            with (
                self.subTest(identifier_type=identifier_type),
                self.assertRaises(EntityIdTypeError),
            ):
                identifier_type("raw")

    def test_line_restore_checks_own_types_positive_quantity_and_saved_equality(
        self,
    ) -> None:
        """Restore не исправляет повреждённые значения и не вычисляет план из произвольного числа."""
        for changes in (
            dict(identifier=uuid4()),
            dict(inventory_item_id=uuid4()),
            dict(sku="RAW"),
            dict(base_uom="KG"),
            dict(planned_qty=Decimal(5)),
            dict(planned_qty=QuantityVO(Decimal(0))),
            dict(conversion=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDocumentLineError),
            ):
                self.restore_line(**changes)
        with self.assertRaises(QuantityConversionMismatchError):
            self.restore_line(planned_qty=QuantityVO(Decimal(6)))
        with self.assertRaises(IncompatibleUomError):
            self.restore_line(base_uom=UomCodeVO("L"))
        restored = self.restore_line()
        self.assertIs(restored.id, self.line.id)
        self.assertIs(restored.sku, self.line.sku)
        self.assertIs(restored.planned_qty, self.line.planned_qty)
        self.assertIs(restored.conversion, self.line.conversion)

    def test_restore_preserves_historical_factor_but_new_use_revalidates_it(
        self,
    ) -> None:
        """Старое равенство количества сохраняется, а повторное использование плана сверяет текущий коэффициент."""
        historical = QuantityConversionSnapshotVO(
            QuantityVO(Decimal(5000)), UomCodeVO("G"), Decimal("0.002")
        )
        line = self.restore_line(
            planned_qty=QuantityVO(Decimal(10)), conversion=historical
        )
        document = self.restore(lines=(line,))
        self.assertIs(document.lines[0].conversion, historical)
        with self.assertRaises(QuantityConversionMismatchError):
            self.confirm(document)
        with self.assertRaises(QuantityConversionMismatchError):
            self.document.add_line(
                line,
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(1),
            )
        fixed = self.change(document, quantity=QuantityVO(Decimal(10000)))
        self.assertEqual(fixed.lines[0].planned_qty.value, Decimal(10))
        self.assertEqual(fixed.lines[0].conversion.factor_to_base, Decimal("0.001"))

    def test_immutable_objects_and_failed_changes_preserve_original_state(self) -> None:
        """Отказ при валидации не меняет план, его строки, даты и версию."""
        with self.assertRaises(QuantityStepError):
            self.change(quantity=QuantityVO(Decimal(1230)))
        self.assertEqual(self.planned.lines, (self.line,))
        self.assertEqual(self.planned.version, 1)
        self.assertEqual(self.planned.updated_at, self.at(1))
        for obj, name, value in (
            (self.planned, "status", StockDocumentStatus.CONFIRMED),
            (self.line, "planned_qty", QuantityVO(Decimal(10))),
            (self.line.conversion, "factor_to_base", Decimal(2)),
        ):
            with self.subTest(obj=type(obj)), self.assertRaises(FrozenInstanceError):
                setattr(obj, name, value)

    def test_raw_dataclass_construction_cannot_bypass_public_method_validation(
        self,
    ) -> None:
        """Все публичные переходы проверяют собственное состояние даже для прямого конструктора."""
        invalid = replace(self.planned, version=True)
        for action in (
            lambda: self.change(invalid),
            lambda: self.confirm(invalid),
            lambda: invalid.get_line(self.line.id),
            lambda: invalid.cancel(updated_at=self.at(3)),
            lambda: invalid.remove_line(self.line.id, updated_at=self.at(3)),
            lambda: invalid.add_line(
                self.create_line(),
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(3),
            ),
        ):
            with self.assertRaises(InvalidStockDocumentValueError):
                action()
        malformed = replace(self.line, planned_qty=QuantityVO(Decimal(0)))
        with self.assertRaises(InvalidStockDocumentLineError):
            self.document.add_line(
                malformed,
                inventory_item=self.item.document_snapshot(),
                updated_at=self.at(1),
            )

    def test_decimal_context_does_not_round_plan_or_modify_global_flags(self) -> None:
        """Создание, изменение и подтверждение точны при враждебной внешней точности и traps."""
        item = replace(self.item, quantity_rules=QuantityRulesVO(Decimal("0.00000001")))
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            line = self.create_line(
                item, quantity=QuantityVO(Decimal("12345678901234567890.12345"))
            )
            document = self.document.add_line(
                line, inventory_item=item.document_snapshot(), updated_at=self.at(1)
            )
            document = document.change_line(
                identifier=line.id,
                quantity=QuantityVO(Decimal("12345678901234567890.12350")),
                uom=UomCodeVO("G"),
                inventory_item=item.document_snapshot(),
                updated_at=self.at(2),
            )
            confirmed = self.confirm(
                document, inventory_items=(item.document_snapshot(),)
            )
            self.assertEqual(
                confirmed.lines[0].planned_qty.value,
                Decimal("12345678901234567.89012350"),
            )
            self.assertFalse(any(context.flags.values()))

    def test_confirm_does_not_create_posting_or_apply_stock_delta(self) -> None:
        """Подтверждённый документ остаётся планом без создания факта журнала или изменения позиций."""
        with (
            patch(
                "src.modules.inventory.domain.stock_posting.aggregate.StockPosting.create",
                side_effect=RuntimeError("Нельзя проводить документ"),
            ),
            patch(
                "src.modules.inventory.domain.stock_position.aggregate.StockPosition.apply_delta",
                side_effect=RuntimeError("Нельзя изменять остаток"),
            ),
        ):
            confirmed = self.confirm()
        self.assertEqual(confirmed.status, StockDocumentStatus.CONFIRMED)
        self.assertNotIn("on_hand_qty", confirmed.__dataclass_fields__)

    def test_policies_validate_direct_inputs_and_own_context_contracts(self) -> None:
        """Чистые Policy требуют типизированный состав и не доверяют отсутствующим снимкам."""
        line_values = dict(
            inventory_item_id=self.line.inventory_item_id,
            base_uom=self.line.base_uom,
            planned_qty=self.line.planned_qty,
            conversion=self.line.conversion,
            inventory_item=self.item.document_snapshot(),
        )
        for changes in (
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(planned_qty=Decimal(5)),
            dict(planned_qty=QuantityVO(Decimal(0))),
            dict(conversion=None),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockDocumentLineError),
            ):
                StockDocumentLinePolicy.ensure_compatible(**(line_values | changes))
        values = dict(
            warehouse_id=self.warehouse.id,
            warehouse=self.warehouse.snapshot(),
            lines=(self.line,),
            inventory_items=(self.item.document_snapshot(),),
        )
        for changes, error in (
            (dict(lines=[]), InvalidStockDocumentLineError),
            (dict(lines=()), EmptyStockDocumentError),
            (dict(lines=(None,)), InvalidStockDocumentLineError),
            (dict(lines=(self.line, self.line)), StockDocumentLineConflictError),
        ):
            with self.subTest(changes=changes), self.assertRaises(error):
                StockDocumentConfirmationPolicy.ensure_confirmable(**(values | changes))


if __name__ == "__main__":
    unittest.main()
