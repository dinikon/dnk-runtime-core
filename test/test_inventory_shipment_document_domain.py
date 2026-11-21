"""Расходный документ из остатков Shipment, сохранение оснований и обязательная повторная проверка подтверждения."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from itertools import permutations
from uuid import UUID, uuid4

from test import test_inventory_shipment_execution_domain as execution_fixture

from src.modules.inventory.domain.error import (
    QuantityConversionMismatchError,
    QuantityStepError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.shipment_execution import (
    ShipmentExecutionPolicy,
)
from src.modules.inventory.domain.shipment.error import (
    InvalidShipmentDocumentSnapshotError,
    ShipmentStatusError,
    InvalidShipmentValueError,
)
from src.modules.inventory.domain.shipment.value_object.execution_binding import (
    ShipmentExecutionBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidDocumentSourceError,
    InvalidDocumentLineSourceError,
    InvalidShipmentDocumentLineBindingError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentLineError,
    StaleShipmentDocumentSourceError,
    StockDocumentShipmentMismatchError,
    StockDocumentShipmentQuantityExceededError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
    StockDocumentNotDraftError,
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
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.shipment_line_binding import (
    ShipmentDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentDocumentDomainTests(unittest.TestCase):
    """Проверяет переход от подтверждённого остатка отправления к самостоятельному универсальному документу."""

    def setUp(self) -> None:
        """Готовит Shipment версии 4 с остатками 1+1 KG и текущим удержанием без его изменения фабрикой."""
        self.flow = execution_fixture.ShipmentExecutionDomainTests()
        self.flow.setUp()
        self.f = self.flow.fixture
        self.shipment = self.flow.register()
        self.time = self.flow.time
        self.bindings = tuple(
            ShipmentDocumentLineBindingVO(line.id, StockDocumentLineIdVO(uuid4()))
            for line in self.shipment.lines
        )

    def build(self, **changes: object) -> StockDocument:
        """Создаёт новый черновик по специализированному снимку и явно переданным ID строк."""
        return StockDocument.create_from_shipment(
            **(
                dict(
                    identifier=StockDocumentIdVO(uuid4()),
                    shipment=self.shipment.document_snapshot(),
                    warehouse=self.f.warehouse,
                    inventory_items=(self.f.item.document_snapshot(),),
                    line_bindings=self.bindings,
                    created_at=self.time,
                )
                | changes
            )
        )

    def confirm(self, document: StockDocument, **changes: object) -> StockDocument:
        """Подтверждает документ с повторным чтением основания и текущими настройками товара."""
        return document.confirm(
            **(
                dict(
                    shipment=self.shipment.document_snapshot(),
                    warehouse=self.f.warehouse,
                    inventory_items=(self.f.item.document_snapshot(),),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def restore(self, document: StockDocument, **changes: object) -> StockDocument:
        """Восстанавливает собственную историю документа без текущего Shipment или товаров."""
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

    def change(self, document: StockDocument, **changes: object) -> StockDocument:
        """Редактирует количество черновика, сохраняя SKU и ссылку основания строки."""
        return document.change_line(
            **(
                dict(
                    identifier=document.lines[0].id,
                    quantity=QuantityVO(Decimal("0.5")),
                    uom=self.f.item.base_uom,
                    inventory_item=self.f.item.document_snapshot(),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def test_document_source_version_is_optional_strict_and_immutable(self) -> None:
        """Внешние основания совместимы с прежними двумя полями; новая версия не принимает bool или дробь."""
        source = DocumentSourceVO(" Sales ", " Order-001 ")
        self.assertEqual(
            (source.system, source.reference, source.version),
            ("Sales", "Order-001", None),
        )
        self.assertEqual(replace(source, version=0).version, 0)
        for value in (True, False, -1, 1.0, Decimal(1), "1"):
            with self.assertRaises(InvalidDocumentSourceError):
                replace(source, version=value)
        with self.assertRaises(FrozenInstanceError):
            source.version = 3

    def test_line_source_is_universal_typed_normalized_and_immutable(self) -> None:
        """Ссылка строки имеет собственный тип, сохраняет регистр/ведущие нули и запрещает управляющие символы."""
        source = DocumentLineSourceVO(" Orders ", " Line-001 ")
        self.assertEqual((source.system, source.reference), ("Orders", "Line-001"))
        for name in ("system", "reference"):
            for value in (None, 1, "", "  ", "a\nb", "a\u200bb"):
                with self.assertRaises(InvalidDocumentLineSourceError):
                    replace(source, **{name: value})
        with self.assertRaises(FrozenInstanceError):
            source.reference = "Other"

    def test_binding_contains_only_two_typed_ids(self) -> None:
        """Новые ID передаются извне, количество и основание не дублируются в назначении."""
        binding = self.bindings[0]
        self.assertEqual(
            set(binding.__dataclass_fields__), {"shipment_line_id", "document_line_id"}
        )
        for changes in (
            dict(shipment_line_id=uuid4()),
            dict(document_line_id=uuid4()),
            dict(document_line_id=self.shipment.id),
        ):
            with self.assertRaises(InvalidShipmentDocumentLineBindingError):
                replace(binding, **changes)
        with self.assertRaises(FrozenInstanceError):
            binding.document_line_id = StockDocumentLineIdVO(uuid4())

    def test_snapshot_getter_is_minimal_frozen_and_validates_original(self) -> None:
        """В снимок документа попадают только идентичность, версия, область и положительные остатки."""
        snapshot = self.shipment.document_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(
            (snapshot.id, snapshot.version, snapshot.status),
            (self.shipment.id, 4, ShipmentStatus.PARTIALLY_SHIPPED),
        )
        self.assertEqual(
            tuple(line.remaining_qty.value for line in snapshot.lines),
            (Decimal(1), Decimal(1)),
        )
        self.assertEqual(
            set(snapshot.lines[0].__dataclass_fields__),
            {"shipment_line_id", "inventory_item_id", "base_uom", "remaining_qty"},
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.version = 0
        with self.assertRaises(InvalidShipmentValueError):
            replace(self.shipment, version=True).document_snapshot()

    def test_factory_builds_complete_issue_draft_version_zero_and_preserves_sources(
        self,
    ) -> None:
        """Новый документ содержит полный остаток, нулевой прогресс и канонические ссылки на версию основания."""
        document = self.build()
        self.assertEqual(
            (document.operation_type, document.status, document.version),
            (StockOperationType.ISSUE, StockDocumentStatus.DRAFT, 0),
        )
        self.assertEqual(
            (
                document.warehouse_id,
                document.owner_id,
                document.created_at,
                document.updated_at,
            ),
            (self.shipment.warehouse_id, self.shipment.owner_id, self.time, self.time),
        )
        self.assertEqual(
            document.source,
            DocumentSourceVO("inventory.shipment", str(self.shipment.id.uuid), 4),
        )
        by_id = {
            value.document_line_id: value.shipment_line_id for value in self.bindings
        }
        for line in document.lines:
            self.assertEqual(
                line.source,
                DocumentLineSourceVO(
                    "inventory.shipment_line", str(by_id[line.id].uuid)
                ),
            )
            self.assertEqual(
                (line.planned_qty.value, line.executed_qty.value),
                (Decimal(1), Decimal(0)),
            )
            self.assertEqual(
                (
                    line.conversion.quantity.value,
                    line.conversion.uom,
                    line.conversion.factor_to_base,
                ),
                (Decimal(1), self.f.item.base_uom, Decimal(1)),
            )
        self.assertEqual(self.shipment.version, 4)
        self.assertEqual(
            (
                self.f.a.reserved_qty.value,
                self.f.b.reserved_qty.value,
                self.f.pool.reserved_qty.value,
            ),
            (Decimal(4), Decimal(3), Decimal(7)),
        )

    def test_full_confirmed_shipment_builds_original_plan_without_merging_same_item(
        self,
    ) -> None:
        """Две строки одного товара остаются отдельными основаниями с независимыми остатками."""
        document = self.build(shipment=self.flow.shipment.document_snapshot())
        by_source = {
            line.source.reference: line.planned_qty.value for line in document.lines
        }
        self.assertEqual(
            by_source,
            {
                str(self.f.line_a.id.uuid): Decimal(3),
                str(self.f.line_b.id.uuid): Decimal(2),
            },
        )
        self.assertEqual(document.source.version, 3)

    def test_closed_rows_are_omitted_and_only_open_item_context_is_required(
        self,
    ) -> None:
        """Полностью отгруженная строка не требует нового ID или снимка её товара."""
        closed = replace(
            self.shipment.lines[0], shipped_qty=self.shipment.lines[0].planned_qty
        )
        shipment = replace(self.shipment, lines=(closed, self.shipment.lines[1]))
        document = self.build(
            shipment=shipment.document_snapshot(), line_bindings=self.bindings[1:]
        )
        self.assertEqual(len(document.lines), 1)
        self.assertEqual(document.lines[0].source.reference, str(self.f.line_b.id.uuid))
        with self.assertRaises(InvalidShipmentDocumentLineBindingError):
            self.build(shipment=shipment.document_snapshot())

    def test_mixed_items_and_dimensions_use_independent_base_quantities_and_contexts(
        self,
    ) -> None:
        """Остатки разных товаров в KG и L строятся независимо без объединения или пересчёта размерностей."""
        snapshot = self.shipment.document_snapshot()
        oil = replace(
            self.f.item.document_snapshot(),
            inventory_item_id=InventoryItemIdVO(uuid4()),
            sku=SkuVO("OIL"),
            base_uom=UomCodeVO("L"),
            quantity_rules=QuantityRulesVO(Decimal("0.5")),
        )
        row = replace(
            snapshot.lines[1],
            inventory_item_id=oil.inventory_item_id,
            base_uom=oil.base_uom,
            remaining_qty=QuantityVO(Decimal("3.5")),
        )
        snapshot = replace(snapshot, lines=(snapshot.lines[0], row))
        items = (self.f.item.document_snapshot(), oil)
        document = self.build(shipment=snapshot, inventory_items=items)
        by_item = {line.inventory_item_id: line for line in document.lines}
        self.assertEqual(
            (
                by_item[oil.inventory_item_id].base_uom,
                by_item[oil.inventory_item_id].planned_qty.value,
                by_item[oil.inventory_item_id].sku,
            ),
            (UomCodeVO("L"), Decimal("3.5"), SkuVO("OIL")),
        )
        self.assertEqual(by_item[self.f.item.id].planned_qty.value, Decimal(1))
        self.assertEqual(
            self.confirm(document, shipment=snapshot, inventory_items=items).status,
            StockDocumentStatus.CONFIRMED,
        )
        with self.assertRaises(InvalidStockDocumentContextError):
            self.build(shipment=snapshot)

    def test_order_of_bindings_and_snapshot_lines_does_not_change_output(self) -> None:
        """Состав упорядочен по UUID строк основания, а не порядку входных соответствий."""
        identifier = StockDocumentIdVO(uuid4())
        expected = self.build(identifier=identifier)
        for bindings in permutations(self.bindings):
            self.assertEqual(
                self.build(identifier=identifier, line_bindings=bindings), expected
            )
        snapshot = self.shipment.document_snapshot()
        self.assertEqual(
            self.build(
                identifier=identifier,
                shipment=replace(snapshot, lines=tuple(reversed(snapshot.lines))),
            ),
            expected,
        )

    def test_factory_rejects_missing_extra_duplicate_and_raw_bindings(self) -> None:
        """Фабрика требует ровно одно назначение на каждую открытую строку и уникальность новых ID."""
        for bindings in (
            (),
            [],
            None,
            (None,),
            self.bindings[:1],
            (*self.bindings, self.bindings[0]),
            (
                self.bindings[0],
                replace(
                    self.bindings[1], document_line_id=self.bindings[0].document_line_id
                ),
            ),
            (
                self.bindings[0],
                replace(self.bindings[1], shipment_line_id=ShipmentLineIdVO(uuid4())),
            ),
        ):
            with self.assertRaises(InvalidShipmentDocumentLineBindingError):
                self.build(line_bindings=bindings)

    def test_factory_rejects_wrong_item_context_and_unit_changes(self) -> None:
        """Текущие снимки нужны ровно для участвующих товаров, базовая единица не переинтерпретируется."""
        item = self.f.item.document_snapshot()
        for items in (
            (),
            [],
            None,
            (item, item),
            (self.f.item,),
            (replace(item, inventory_item_id=InventoryItemIdVO(uuid4())),),
            (item, replace(item, inventory_item_id=InventoryItemIdVO(uuid4()))),
        ):
            with self.assertRaises(
                (
                    InvalidStockDocumentContextError,
                    InvalidInventoryItemDocumentSnapshotError,
                )
            ):
                self.build(inventory_items=items)
        with self.assertRaises(StockDocumentUomMismatchError):
            self.build(inventory_items=(replace(item, base_uom=UomCodeVO("G")),))

    def test_factory_requires_same_active_warehouse_and_valid_status(self) -> None:
        """Черновик, отменённый и завершённый Shipment не создают расходные документы."""
        for warehouse, error in (
            (None, InvalidWarehouseSnapshotError),
            (
                replace(self.f.warehouse, id=WarehouseIdVO(uuid4())),
                InvalidStockDocumentContextError,
            ),
            (replace(self.f.warehouse, is_active=False), WarehouseInactiveError),
        ):
            with self.assertRaises(error):
                self.build(warehouse=warehouse)
        full = replace(
            self.shipment,
            status=ShipmentStatus.SHIPPED,
            lines=tuple(
                replace(line, shipped_qty=line.planned_qty)
                for line in self.shipment.lines
            ),
        )
        for shipment in (self.f.draft(), self.f.cancel(self.f.draft()), full):
            with self.assertRaises(ShipmentStatusError):
                self.build(shipment=shipment.document_snapshot())

    def test_snapshot_is_revalidated_and_wrong_purpose_snapshots_are_rejected(
        self,
    ) -> None:
        """Аннотации и frozen не заменяют проверку структуры на границе Domain-решения."""
        snapshot = self.shipment.document_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(version=True),
            dict(version=-1),
            dict(status="PARTIALLY_SHIPPED"),
            dict(warehouse_id=None),
            dict(owner_id=None),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=(None,)),
            dict(lines=()),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(status=ShipmentStatus.SHIPPED),
        ):
            with self.assertRaises(InvalidShipmentDocumentSnapshotError):
                self.build(shipment=replace(snapshot, **changes))
        for changes in (
            dict(shipment_line_id=uuid4()),
            dict(inventory_item_id=None),
            dict(base_uom=None),
            dict(remaining_qty=Decimal(1)),
            dict(remaining_qty=QuantityVO(Decimal(0))),
        ):
            with self.assertRaises(InvalidShipmentDocumentSnapshotError):
                self.build(
                    shipment=replace(
                        snapshot, lines=(replace(snapshot.lines[0], **changes),)
                    )
                )
        for value in (self.shipment, None, self.shipment.execution_snapshot()):
            with self.assertRaises(InvalidShipmentDocumentSnapshotError):
                self.build(shipment=value)

    def test_factory_time_is_explicit_aware_normalized_and_not_before_basis(
        self,
    ) -> None:
        """Время решения не читается автоматически и не предшествует состоянию отправления."""
        for value in (
            None,
            "now",
            self.time.replace(tzinfo=None),
            self.time - timedelta(seconds=1),
        ):
            with self.assertRaises(StockDocumentTimeError):
                self.build(created_at=value)
        self.assertEqual(
            self.build(
                created_at=self.time.astimezone(timezone(timedelta(hours=2)))
            ).created_at,
            self.time,
        )

    def test_current_step_and_sku_are_used_without_reinterpreting_historical_input(
        self,
    ) -> None:
        """Документ фиксирует текущий SKU, базовый ввод и шаг; исходный пересчёт отправления не меняется."""
        current = replace(self.f.item.document_snapshot(), sku=SkuVO("NEW-SKU"))
        document = self.build(inventory_items=(current,))
        self.assertTrue(all(line.sku == current.sku for line in document.lines))
        with self.assertRaises(QuantityStepError):
            self.build(
                inventory_items=(
                    replace(current, quantity_rules=QuantityRulesVO(Decimal(2))),
                )
            )
        historical = replace(
            self.shipment.lines[0],
            conversion=replace(
                self.shipment.lines[0].conversion,
                quantity=QuantityVO(Decimal("1.5")),
                factor_to_base=Decimal(2),
            ),
        )
        shipment = replace(self.shipment, lines=(historical, self.shipment.lines[1]))
        doc = self.build(shipment=shipment.document_snapshot())
        self.assertTrue(
            all(line.conversion.factor_to_base == Decimal(1) for line in doc.lines)
        )
        self.assertEqual(shipment.lines[0].conversion.factor_to_base, Decimal(2))

    def test_serial_and_lot_serial_documents_plan_whole_pcs_without_selecting_instances(
        self,
    ) -> None:
        """Остаток SERIAL остаётся целым PCS; серии не выбираются при построении документа."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = replace(
                self.f.item.document_snapshot(),
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
            )
            snapshot = self.shipment.document_snapshot()
            snapshot = replace(
                snapshot,
                lines=tuple(
                    replace(line, base_uom=item.base_uom) for line in snapshot.lines
                ),
            )
            document = self.build(shipment=snapshot, inventory_items=(item,))
            confirmed = self.confirm(
                document, shipment=snapshot, inventory_items=(item,)
            )
            self.assertTrue(
                all(
                    line.base_uom == UomCodeVO("PCS")
                    and line.planned_qty.value == Decimal(1)
                    for line in confirmed.lines
                )
            )

    def test_confirmation_requires_basis_even_when_using_existing_generic_method(
        self,
    ) -> None:
        """Обычный confirm не позволяет обойти повторную проверку отправления."""
        document = self.build()
        with self.assertRaises(InvalidShipmentDocumentSnapshotError):
            document.confirm(
                warehouse=self.f.warehouse,
                inventory_items=(self.f.item.document_snapshot(),),
                updated_at=self.time,
            )
        for value in (None, self.shipment, self.shipment.execution_snapshot()):
            with self.assertRaises(InvalidShipmentDocumentSnapshotError):
                self.confirm(document, shipment=value)
        confirmed = self.confirm(document)
        self.assertEqual(
            (confirmed.status, confirmed.version), (StockDocumentStatus.CONFIRMED, 1)
        )
        with self.assertRaises(StockDocumentNotDraftError):
            self.confirm(confirmed)

    def test_confirmation_rejects_stale_version_including_unrelated_basis_updates(
        self,
    ) -> None:
        """Версия основания фиксируется при построении и не обновляется автоматически при подтверждении."""
        document = self.build()
        snapshot = self.shipment.document_snapshot()
        with self.assertRaises(StaleShipmentDocumentSourceError):
            self.confirm(
                document, shipment=replace(snapshot, version=snapshot.version + 1)
            )
        fact = self.flow.fact(("0.5",))
        registration = self.flow.build(
            shipment=self.shipment.execution_snapshot(),
            execution=fact.reservation_snapshot(),
            bindings=(
                ShipmentExecutionBindingVO(fact.lines[0].id, self.shipment.lines[0].id),
            ),
        )
        partial = self.shipment.register_execution(
            registration, expected_version=4, updated_at=self.time
        )
        with self.assertRaises(StaleShipmentDocumentSourceError):
            self.confirm(document, shipment=partial.document_snapshot())
        self.assertEqual(document.source.version, 4)

    def test_confirmation_rechecks_basis_identity_area_status_and_time(self) -> None:
        """Повторная проверка запрещает другой Shipment, область, неподходящий статус или будущий снимок."""
        document = self.build()
        snapshot = self.shipment.document_snapshot()
        for changes in (
            dict(id=ShipmentIdVO(uuid4())),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
        ):
            with self.assertRaises(StockDocumentShipmentMismatchError):
                self.confirm(document, shipment=replace(snapshot, **changes))
        for status in (ShipmentStatus.DRAFT, ShipmentStatus.CANCELLED):
            with self.assertRaises(ShipmentStatusError):
                self.confirm(document, shipment=replace(snapshot, status=status))
        with self.assertRaises(ShipmentStatusError):
            self.confirm(
                document,
                shipment=replace(snapshot, status=ShipmentStatus.SHIPPED, lines=()),
            )
        with self.assertRaises(StockDocumentTimeError):
            self.confirm(
                document,
                shipment=replace(snapshot, updated_at=self.time + timedelta(seconds=1)),
            )

    def test_confirmation_rechecks_limits_membership_item_unit_and_current_step(
        self,
    ) -> None:
        """Увеличить черновик можно, но подтвердить сверх остатка или подменить товар/единицу нельзя."""
        document = self.build()
        oversized = self.change(document, quantity=QuantityVO(Decimal("1.05")))
        with self.assertRaises(StockDocumentShipmentQuantityExceededError):
            self.confirm(oversized)
        snapshot = self.shipment.document_snapshot()
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
            dict(shipment_line_id=ShipmentLineIdVO(uuid4())),
        ):
            with self.assertRaises(StockDocumentShipmentMismatchError):
                self.confirm(
                    document,
                    shipment=replace(
                        snapshot,
                        lines=(
                            replace(snapshot.lines[0], **changes),
                            *snapshot.lines[1:],
                        ),
                    ),
                )
        with self.assertRaises(QuantityStepError):
            self.confirm(
                document,
                inventory_items=(
                    replace(
                        self.f.item.document_snapshot(),
                        quantity_rules=QuantityRulesVO(Decimal(2)),
                    ),
                ),
            )

    def test_edited_quantities_preserve_line_origin_sku_and_basis_version(self) -> None:
        """Редактирование сохраняет все основания и исторический SKU, даже при смене исходной единицы."""
        document = self.build()
        changed = self.change(
            document,
            quantity=QuantityVO(Decimal(500)),
            uom=UomCodeVO("G"),
            inventory_item=replace(self.f.item.document_snapshot(), sku=SkuVO("NEW")),
        )
        self.assertEqual(changed.lines[0].source, document.lines[0].source)
        self.assertEqual(changed.lines[0].sku, document.lines[0].sku)
        self.assertEqual(changed.source, document.source)
        self.assertEqual(changed.lines[0].planned_qty.value, Decimal("0.5"))
        self.assertEqual(self.confirm(changed).status, StockDocumentStatus.CONFIRMED)

    def test_removed_rows_allow_subset_but_empty_document_cannot_confirm(self) -> None:
        """Черновик можно уменьшить до части отправления без требования покрыть все строки основания."""
        document = self.build()
        subset = document.remove_line(document.lines[0].id, updated_at=self.time)
        self.assertEqual(len(self.confirm(subset).lines), 1)
        empty = subset.remove_line(subset.lines[0].id, updated_at=self.time)
        with self.assertRaises(EmptyStockDocumentError):
            self.confirm(empty)

    def test_linked_document_rejects_missing_foreign_or_duplicate_line_origins(
        self,
    ) -> None:
        """Собственные инварианты корня защищают основания уже при редактировании и восстановлении."""
        document = self.build()
        line = document.lines[0]
        for source in (
            None,
            DocumentLineSourceVO("external", "1"),
            DocumentLineSourceVO("inventory.shipment_line", "not-uuid"),
            DocumentLineSourceVO(
                "inventory.shipment_line",
                str(self.shipment.lines[0].id.uuid).replace("-", ""),
            ),
        ):
            with self.assertRaises(StockDocumentShipmentMismatchError):
                self.restore(document, lines=(replace(line, source=source),))
        duplicate = replace(line, id=StockDocumentLineIdVO(uuid4()))
        with self.assertRaises(StockDocumentShipmentMismatchError):
            document.add_line(
                duplicate,
                inventory_item=self.f.item.document_snapshot(),
                updated_at=self.time,
            )
        foreign = replace(
            line,
            id=StockDocumentLineIdVO(uuid4()),
            source=DocumentLineSourceVO(
                "inventory.shipment_line", str(ShipmentLineIdVO(uuid4()).uuid)
            ),
        )
        expanded = document.add_line(
            foreign,
            inventory_item=self.f.item.document_snapshot(),
            updated_at=self.time,
        )
        with self.assertRaises(StockDocumentShipmentMismatchError):
            self.confirm(expanded)

    def test_reserved_origin_requires_issue_version_and_canonical_header_id(
        self,
    ) -> None:
        """Зарезервированная система основания не допускает чужой тип операции или потерю версии/шапки."""
        document = self.build()
        for changes in (
            dict(operation_type=StockOperationType.RECEIPT),
            dict(operation_type=StockOperationType.INTERNAL_MOVE),
            dict(source=replace(document.source, version=None)),
            dict(source=replace(document.source, reference="not-uuid")),
            dict(
                source=replace(
                    document.source,
                    reference=document.source.reference.replace("-", ""),
                )
            ),
            dict(source=None),
            dict(source=DocumentSourceVO("external", "order")),
        ):
            with self.assertRaises(StockDocumentShipmentMismatchError):
                self.restore(document, **changes)

    def test_generic_documents_keep_optional_independent_sources_and_old_confirmation(
        self,
    ) -> None:
        """Универсальные документы с внешними основаниями по-прежнему подтверждаются без Shipment."""
        source = DocumentLineSourceVO("external.order_line", "0001")
        line = StockDocumentLine.create(
            identifier=StockDocumentLineIdVO(uuid4()),
            inventory_item=self.f.item.document_snapshot(),
            quantity=QuantityVO(Decimal(1)),
            uom=self.f.item.base_uom,
            source=source,
        )
        document = StockDocument.create(
            identifier=StockDocumentIdVO(uuid4()),
            operation_type=StockOperationType.RECEIPT,
            warehouse=self.f.warehouse,
            owner_id=self.f.owner,
            source=DocumentSourceVO("external.order", "001", 0),
            created_at=self.time,
        )
        document = document.add_line(
            line, inventory_item=self.f.item.document_snapshot(), updated_at=self.time
        )
        confirmed = self.confirm(document, shipment=None)
        self.assertEqual(confirmed.lines[0].source, source)
        with self.assertRaises(InvalidStockDocumentContextError):
            self.confirm(document)
        with self.assertRaises(InvalidStockDocumentLineError):
            replace(line, source=DocumentSourceVO("external", "1")).ensure_valid()

    def test_restore_preserves_own_history_without_requiring_current_basis(
        self,
    ) -> None:
        """Восстановление не подтверждает текущие остатки, но сохраняет ссылки, SKU и исторический коэффициент."""
        document = self.confirm(self.build())
        historical = replace(
            document.lines[0],
            planned_qty=QuantityVO(Decimal(2)),
            conversion=replace(document.lines[0].conversion, factor_to_base=Decimal(2)),
        )
        restored = self.restore(
            document, lines=(historical,), source=replace(document.source, version=0)
        )
        self.assertEqual(restored.lines[0], historical)
        self.assertEqual(restored.source.version, 0)
        self.assertEqual(self.restore(restored), restored)
        draft = self.restore(restored, status=StockDocumentStatus.DRAFT)
        with self.assertRaises(QuantityConversionMismatchError):
            self.confirm(draft)

    def test_exact_remaining_arithmetic_ignores_hostile_decimal_context(self) -> None:
        """Получение остатка и построение документа не округляют значения внешним Decimal context."""
        shipment = replace(
            self.shipment,
            lines=(
                replace(
                    self.shipment.lines[0], shipped_qty=QuantityVO(Decimal("1.95"))
                ),
                self.shipment.lines[1],
            ),
        )
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            document = self.build(shipment=shipment.document_snapshot())
            by_source = {
                line.source.reference: line.planned_qty.value for line in document.lines
            }
            self.assertEqual(
                by_source[str(self.shipment.lines[0].id.uuid)], Decimal("1.05")
            )

    def test_created_document_can_execute_and_complete_shipment_through_existing_path(
        self,
    ) -> None:
        """Документ с остатком 1+1 KG исполняется прежним механизмом и завершает исходный Shipment."""
        document = self.confirm(self.build())
        lines = tuple(
            StockExecutionLine.create(
                identifier=StockExecutionLineIdVO(uuid4()),
                document_line_id=line.id,
                inventory_item=self.f.item.execution_snapshot(),
                quantity=line.planned_qty,
                uom=line.base_uom,
                route=IssueExecutionRouteVO(self.flow.position.dimensions),
            )
            for line in document.lines
        )
        execution = StockExecution.create(
            identifier=StockExecutionIdVO(uuid4()),
            document=document.execution_snapshot(),
            executed_at=self.time,
            lines=lines,
            warehouse=self.f.warehouse,
            inventory_items=(self.f.item.execution_snapshot(),),
            locations=(self.flow.location,),
        )
        by_document_line = {line.id: line for line in document.lines}
        registration = ShipmentExecutionPolicy.build_registration(
            shipment=self.shipment.execution_snapshot(),
            execution=execution.reservation_snapshot(),
            bindings=tuple(
                ShipmentExecutionBindingVO(
                    line.id,
                    ShipmentLineIdVO(
                        UUID(by_document_line[line.document_line_id].source.reference)
                    ),
                )
                for line in execution.lines
            ),
        )
        completed = self.shipment.register_execution(
            registration, expected_version=4, updated_at=self.time
        )
        document_after = document.register_execution(
            execution.snapshot_for_document(), updated_at=self.time
        )
        self.assertEqual(completed.status, ShipmentStatus.SHIPPED)
        self.assertEqual(document_after.status, StockDocumentStatus.COMPLETED)
        self.assertEqual(
            tuple(line.source for line in document_after.lines),
            tuple(line.source for line in document.lines),
        )

    def test_building_twice_does_not_claim_cross_document_quantity_allocation(
        self,
    ) -> None:
        """Повторное построение по тому же остатку допустимо локально и требует внешнего контроля назначений."""
        first, second = self.build(), self.build()
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.source, second.source)
        self.assertEqual(self.confirm(first).status, StockDocumentStatus.CONFIRMED)
        self.assertEqual(self.confirm(second).status, StockDocumentStatus.CONFIRMED)


if __name__ == "__main__":
    unittest.main()
