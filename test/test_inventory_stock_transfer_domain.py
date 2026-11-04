"""Первый план межскладского перемещения: направление, строки, версии и подтверждение без физического движения."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, MAX_EMAX, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    InvalidQuantityConversionError,
    InventoryError,
    QuantityConversionMismatchError,
    QuantityStepError,
    UomConversionError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
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
from src.modules.inventory.domain.policy.stock_transfer_confirmation import (
    StockTransferConfirmationPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_line import (
    StockTransferLinePolicy,
)
from src.modules.inventory.domain.stock_transfer.aggregate import StockTransfer
from src.modules.inventory.domain.stock_transfer.entity.transfer_line import (
    TransferLine,
)
from src.modules.inventory.domain.stock_transfer.error import (
    EmptyStockTransferError,
    InvalidStockTransferContextError,
    InvalidStockTransferLineError,
    InvalidStockTransferValueError,
    StockTransferItemMismatchError,
    StockTransferLineConflictError,
    StockTransferLineNotFoundError,
    StockTransferSameWarehouseError,
    StockTransferStatusError,
    StockTransferTimeError,
    StockTransferUomMismatchError,
    StockTransferVersionConflictError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.domain_error import EntityIdTypeError


class StockTransferDomainTests(unittest.TestCase):
    """Проверяет небольшую границу агрегата перемещения без складских фактов, остатков или резервов."""

    def setUp(self) -> None:
        """Готовит два активных склада без локаций и зерно с планом 50000 G = 50 KG и шагом 0.05 KG."""
        self.time = datetime(2026, 11, 4, 12, tzinfo=UTC)
        self.source = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.destination = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.owner = StockOwnerIdVO(uuid4())
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("GRAIN"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.line = self.new_line(
            quantity=QuantityVO(Decimal(50000)), uom=UomCodeVO("G")
        )

    def create(self, **changes: object) -> StockTransfer:
        """Создаёт пустой черновик с явными идентичностью, направлением, владельцем и временем."""
        return StockTransfer.create(
            **(
                dict(
                    identifier=StockTransferIdVO(uuid4()),
                    source_warehouse=self.source,
                    destination_warehouse=self.destination,
                    owner_id=self.owner,
                    created_at=self.time,
                )
                | changes
            )
        )

    def new_line(self, **changes: object) -> TransferLine:
        """Формирует строку по текущему снимку товара без выбора партии, серии или локации."""
        return TransferLine.create(
            **(
                dict(
                    identifier=StockTransferLineIdVO(uuid4()),
                    inventory_item=self.item.stock_snapshot(),
                    quantity=QuantityVO(Decimal(50)),
                    uom=self.item.base_uom,
                )
                | changes
            )
        )

    def restore_line(self, **changes: object) -> TransferLine:
        """Восстанавливает полный собственный состав строки со всеми историческими значениями."""
        return TransferLine.restore(
            **(
                dict(
                    identifier=self.line.id,
                    inventory_item_id=self.line.inventory_item_id,
                    base_uom=self.line.base_uom,
                    planned_qty=self.line.planned_qty,
                    conversion=self.line.conversion,
                )
                | changes
            )
        )

    def restore(
        self, reference: StockTransfer | None = None, **changes: object
    ) -> StockTransfer:
        """Восстанавливает полный собственный состав без текущего состояния складов и товаров."""
        reference = self.create() if reference is None else reference
        return StockTransfer.restore(
            **(
                dict(
                    identifier=reference.id,
                    source_warehouse_id=reference.source_warehouse_id,
                    destination_warehouse_id=reference.destination_warehouse_id,
                    owner_id=reference.owner_id,
                    status=reference.status,
                    lines=reference.lines,
                    created_at=reference.created_at,
                    updated_at=reference.updated_at,
                    version=reference.version,
                )
                | changes
            )
        )

    def add(
        self,
        transfer: StockTransfer | None = None,
        line: TransferLine | None = None,
        **changes: object,
    ) -> StockTransfer:
        """Добавляет строку с текущей ожидаемой версией и явно указанным временем."""
        transfer = self.create() if transfer is None else transfer
        return transfer.add_line(
            self.line if line is None else line,
            **(
                dict(
                    expected_version=transfer.version,
                    inventory_item=self.item.stock_snapshot(),
                    updated_at=self.time,
                )
                | changes
            ),
        )

    def change(
        self, transfer: StockTransfer | None = None, **changes: object
    ) -> StockTransfer:
        """Изменяет ввод первой строки, сохраняя её идентичность и товар."""
        transfer = self.add() if transfer is None else transfer
        return transfer.change_line_quantity(
            **(
                dict(
                    identifier=self.line.id,
                    quantity=QuantityVO(Decimal(10)),
                    uom=self.item.base_uom,
                    expected_version=transfer.version,
                    inventory_item=self.item.stock_snapshot(),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def remove(
        self, transfer: StockTransfer | None = None, **changes: object
    ) -> StockTransfer:
        """Удаляет первую строку черновика без актуальных внешних снимков."""
        transfer = self.add() if transfer is None else transfer
        return transfer.remove_line(
            **(
                dict(
                    identifier=self.line.id,
                    expected_version=transfer.version,
                    updated_at=self.time,
                )
                | changes
            )
        )

    def confirm(
        self, transfer: StockTransfer | None = None, **changes: object
    ) -> StockTransfer:
        """Подтверждает план по новым снимкам обоих складов и ровно участвующих товаров."""
        transfer = self.add() if transfer is None else transfer
        return transfer.confirm(
            **(
                dict(
                    expected_version=transfer.version,
                    source_warehouse=self.source,
                    destination_warehouse=self.destination,
                    inventory_items=(self.item.stock_snapshot(),),
                    updated_at=self.time,
                )
                | changes
            )
        )

    def cancel(
        self, transfer: StockTransfer | None = None, **changes: object
    ) -> StockTransfer:
        """Отменяет черновик по явной версии без побочных изменений учётных агрегатов."""
        transfer = self.create() if transfer is None else transfer
        return transfer.cancel(
            **(dict(expected_version=transfer.version, updated_at=self.time) | changes)
        )

    def test_identifiers_are_typed_immutable_uuid_values(self) -> None:
        """Корень и строка имеют собственные типы идентичности, произвольные строки не принимаются."""
        for cls in (StockTransferIdVO, StockTransferLineIdVO):
            value = cls(uuid4())
            with self.assertRaises(EntityIdTypeError):
                cls(str(value.uuid))
            with self.assertRaises(FrozenInstanceError):
                value.value = uuid4()

    def test_create_empty_draft_does_not_require_physical_locations_or_stock(
        self,
    ) -> None:
        """Пустой план версии 0 создаётся между активными складами даже без основных локаций и наличия."""
        transfer = self.create()
        self.assertEqual(
            (
                transfer.status,
                transfer.lines,
                transfer.version,
                transfer.created_at,
                transfer.updated_at,
            ),
            (StockTransferStatus.DRAFT, (), 0, self.time, self.time),
        )
        self.assertEqual(
            (
                transfer.source_warehouse_id,
                transfer.destination_warehouse_id,
                transfer.owner_id,
            ),
            (self.source.id, self.destination.id, self.owner),
        )
        self.assertEqual(
            set(transfer.__dataclass_fields__),
            {
                "id",
                "source_warehouse_id",
                "destination_warehouse_id",
                "owner_id",
                "status",
                "lines",
                "created_at",
                "updated_at",
                "version",
            },
        )

    def test_same_warehouse_is_rejected_at_creation_restore_and_policy(self) -> None:
        """Различие складов — собственный инвариант, который нельзя обойти восстановлением."""
        with self.assertRaises(StockTransferSameWarehouseError):
            self.create(destination_warehouse=self.source)
        with self.assertRaises(StockTransferSameWarehouseError):
            self.restore(destination_warehouse_id=self.source.id)
        with self.assertRaises(StockTransferSameWarehouseError):
            StockTransferConfirmationPolicy.ensure_warehouses(
                source_warehouse_id=self.source.id,
                destination_warehouse_id=self.source.id,
                source_warehouse=self.source,
                destination_warehouse=self.source,
            )

    def test_both_warehouses_must_be_active_and_snapshots_are_revalidated(self) -> None:
        """Активность, тип снимка и настоящий bool проверяются для каждой стороны направления."""
        for field in ("source_warehouse", "destination_warehouse"):
            warehouse = self.source if field == "source_warehouse" else self.destination
            with self.assertRaises(WarehouseInactiveError):
                self.create(**{field: replace(warehouse, is_active=False)})
            for raw in (None, warehouse.id):
                with self.assertRaises(InvalidWarehouseSnapshotError):
                    self.create(**{field: raw})
            with self.assertRaises(InvalidWarehouseSnapshotError):
                self.create(**{field: replace(warehouse, is_active=1)})
        for changes in (dict(identifier=uuid4()), dict(owner_id=uuid4())):
            with self.assertRaises(InvalidStockTransferValueError):
                self.create(**changes)

    def test_line_preserves_input_and_exact_base_quantity_without_extra_state(
        self,
    ) -> None:
        """В строке сохранены исходные 50000 G, коэффициент 0.001 и план 50 KG без прогресса или резервов."""
        line = self.line
        self.assertEqual(
            (
                line.planned_qty.value,
                line.base_uom,
                line.conversion.quantity.value,
                line.conversion.uom,
                line.conversion.factor_to_base,
            ),
            (
                Decimal(50),
                UomCodeVO("KG"),
                Decimal(50000),
                UomCodeVO("G"),
                Decimal("0.001"),
            ),
        )
        self.assertEqual(
            set(line.__dataclass_fields__),
            {"id", "inventory_item_id", "base_uom", "planned_qty", "conversion"},
        )
        with self.assertRaises(FrozenInstanceError):
            line.planned_qty = QuantityVO(Decimal(1))

    def test_line_creation_requires_positive_quantity_current_step_and_valid_units(
        self,
    ) -> None:
        """Ноль, некратное количество и несовместимые размерности не формируют новую строку."""
        with self.assertRaises(InvalidQuantityConversionError):
            self.new_line(quantity=QuantityVO(Decimal(0)))
        with self.assertRaises(QuantityStepError):
            self.new_line(quantity=QuantityVO(Decimal("0.01")))
        with self.assertRaises(IncompatibleUomError):
            self.new_line(uom=UomCodeVO("L"))
        with self.assertRaises(UnknownUomError):
            self.new_line(uom=UomCodeVO("UNKNOWN"))
        for raw in (None, Decimal(1)):
            with self.assertRaises(InventoryError):
                self.new_line(quantity=raw)

    def test_full_or_wrong_purpose_item_objects_cannot_replace_stock_snapshot(
        self,
    ) -> None:
        """Фабрика, редактирование и подтверждение принимают только соответствующие учётные снимки."""
        for value in (None, self.item, self.item.document_snapshot()):
            with self.assertRaises(InvalidInventoryItemStockSnapshotError):
                self.new_line(inventory_item=value)
            with self.assertRaises(InvalidInventoryItemStockSnapshotError):
                self.change(inventory_item=value)
            with self.assertRaises(InvalidInventoryItemStockSnapshotError):
                self.confirm(inventory_items=(value,))
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.new_line(
                inventory_item=replace(
                    self.item.stock_snapshot(), quantity_rules=Decimal(1)
                )
            )

    def test_repeated_item_lines_are_kept_separate_and_use_one_item_snapshot(
        self,
    ) -> None:
        """Одинаковые товары не объединяются; уникальны ID строк, а не товары или исходные единицы."""
        second = self.new_line(quantity=QuantityVO(Decimal("0.5")))
        planned = self.add(self.add(), second)
        confirmed = self.confirm(planned)
        self.assertEqual(
            (confirmed.version, len(confirmed.lines), confirmed.status),
            (3, 2, StockTransferStatus.CONFIRMED),
        )
        self.assertEqual(
            tuple(line.planned_qty.value for line in confirmed.lines),
            (Decimal(50), Decimal("0.5")),
        )
        with self.assertRaises(StockTransferLineConflictError):
            self.add(self.add())

    def test_add_change_remove_preserve_header_and_increment_each_real_change(
        self,
    ) -> None:
        """Направление, владелец и идентичность не меняются при операциях над дочерними строками."""
        empty = self.create()
        added = self.add(empty)
        changed = self.change(added)
        removed = self.remove(changed)
        self.assertEqual(
            (empty.version, added.version, changed.version, removed.version),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            (
                changed.lines[0].id,
                changed.lines[0].inventory_item_id,
                changed.lines[0].base_uom,
            ),
            (self.line.id, self.item.id, self.item.base_uom),
        )
        self.assertEqual(removed.lines, ())
        for transfer in (added, changed, removed):
            self.assertEqual(
                (
                    transfer.id,
                    transfer.source_warehouse_id,
                    transfer.destination_warehouse_id,
                    transfer.owner_id,
                    transfer.created_at,
                ),
                (empty.id, self.source.id, self.destination.id, self.owner, self.time),
            )
        with self.assertRaises(FrozenInstanceError):
            changed.destination_warehouse_id = self.source.id

    def test_numerically_equal_input_is_noop_only_after_validation(self) -> None:
        """Равный ввод в той же единице сохраняет объект/версию/время; изменение исходной единицы меняет историю."""
        planned = self.add()
        same = self.change(
            planned,
            quantity=QuantityVO(Decimal("50000.00")),
            uom=UomCodeVO("G"),
            updated_at=self.time + timedelta(minutes=1),
        )
        self.assertIs(same, planned)
        self.assertEqual(same.updated_at, self.time)
        changed = self.change(planned, quantity=QuantityVO(Decimal(50)))
        self.assertEqual(
            (changed.version, changed.lines[0].planned_qty),
            (2, planned.lines[0].planned_qty),
        )
        self.assertEqual(changed.lines[0].conversion.uom, UomCodeVO("KG"))
        with self.assertRaises(QuantityStepError):
            self.change(
                planned,
                quantity=QuantityVO(Decimal(50000)),
                uom=UomCodeVO("G"),
                inventory_item=replace(
                    self.item.stock_snapshot(),
                    quantity_rules=QuantityRulesVO(Decimal(3)),
                ),
            )

    def test_quantity_change_cannot_reassign_item_or_base_unit(self) -> None:
        """Текущий снимок другого товара или новой базовой единицы не меняет смысл старой строки."""
        with self.assertRaises(StockTransferItemMismatchError):
            self.change(
                inventory_item=replace(
                    self.item.stock_snapshot(),
                    inventory_item_id=InventoryItemIdVO(uuid4()),
                )
            )
        with self.assertRaises(StockTransferUomMismatchError):
            self.change(
                inventory_item=replace(
                    self.item.stock_snapshot(), base_uom=UomCodeVO("G")
                )
            )

    def test_unknown_or_untyped_line_ids_are_rejected(self) -> None:
        """Изменение и удаление находят строки только в данном агрегате по собственному типу ID."""
        for operation in (self.change, self.remove):
            with self.assertRaises(StockTransferLineNotFoundError):
                operation(identifier=StockTransferLineIdVO(uuid4()))
            for value in (None, uuid4(), self.item.id):
                with self.assertRaises(InvalidStockTransferLineError):
                    operation(identifier=value)
        for value in (None, self.line.conversion, self.item):
            with self.assertRaises(InvalidStockTransferLineError):
                self.create().add_line(
                    value,
                    expected_version=0,
                    inventory_item=self.item.stock_snapshot(),
                    updated_at=self.time,
                )

    def test_confirmation_rechecks_both_warehouse_identities_and_activity(self) -> None:
        """Деактивация, чужой склад или перестановка направления после создания препятствуют подтверждению."""
        planned = self.add()
        for field, warehouse in (
            ("source_warehouse", self.source),
            ("destination_warehouse", self.destination),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.confirm(planned, **{field: replace(warehouse, is_active=False)})
            with self.assertRaises(InvalidStockTransferContextError):
                self.confirm(
                    planned, **{field: replace(warehouse, id=WarehouseIdVO(uuid4()))}
                )
            with self.assertRaises(InvalidWarehouseSnapshotError):
                self.confirm(planned, **{field: None})
        with self.assertRaises(InvalidStockTransferContextError):
            self.confirm(
                planned,
                source_warehouse=self.destination,
                destination_warehouse=self.source,
            )

    def test_confirmation_requires_exact_unique_current_item_set(self) -> None:
        """Отсутствующие, повторные и лишние снимки не допускаются; каждый новый товар проверяется отдельно."""
        snapshot = self.item.stock_snapshot()
        for values in (
            (),
            [],
            None,
            (snapshot, snapshot),
            (snapshot, replace(snapshot, inventory_item_id=InventoryItemIdVO(uuid4()))),
            (replace(snapshot, inventory_item_id=InventoryItemIdVO(uuid4())),),
        ):
            with self.assertRaises(InvalidStockTransferContextError):
                self.confirm(inventory_items=values)
        with self.assertRaises(StockTransferUomMismatchError):
            self.confirm(inventory_items=(replace(snapshot, base_uom=UomCodeVO("G")),))
        with self.assertRaises(QuantityStepError):
            self.confirm(
                inventory_items=(
                    replace(snapshot, quantity_rules=QuantityRulesVO(Decimal(3))),
                )
            )

    def test_empty_confirmation_is_rejected_but_empty_draft_cancellation_is_valid(
        self,
    ) -> None:
        """Пустой черновик допустим, подтверждённый план всегда непустой, отмена сохраняет полный состав."""
        with self.assertRaises(EmptyStockTransferError):
            self.confirm(self.create(), inventory_items=())
        empty = self.cancel()
        planned = self.add()
        cancelled = self.cancel(planned)
        self.assertEqual(
            (empty.status, empty.lines, empty.version),
            (StockTransferStatus.CANCELLED, (), 1),
        )
        self.assertEqual((cancelled.lines, cancelled.version), (planned.lines, 2))

    def test_only_draft_allows_any_mutation_or_cancellation(self) -> None:
        """Подтверждённый и отменённый план не редактируется, не подтверждается и не отменяется повторно."""
        for transfer in (self.confirm(), self.cancel(self.add())):
            for operation in (
                self.add,
                self.change,
                self.remove,
                self.confirm,
                self.cancel,
            ):
                with self.assertRaises(StockTransferStatusError):
                    operation(transfer)

    def test_all_mutations_require_strict_current_and_expected_versions(self) -> None:
        """bool, отрицательные и нецелые версии не подменяют проверку конкурентного изменения."""
        planned = self.add()
        for operation in (
            self.add,
            self.change,
            self.remove,
            self.confirm,
            self.cancel,
        ):
            for value in (True, False, -1, "1", Decimal(1), 1.0, None):
                with self.assertRaises(InvalidStockTransferValueError):
                    operation(planned, expected_version=value)
            with self.assertRaises(StockTransferVersionConflictError):
                operation(planned, expected_version=0)
            for value in (True, -1, "1"):
                with self.assertRaises(InvalidStockTransferValueError):
                    operation(replace(planned, version=value), expected_version=1)

    def test_version_conflict_precedes_policy_and_historical_quantity_arithmetic(
        self,
    ) -> None:
        """При конфликте версии собственные строки и внешние Policy не вызываются."""
        planned = self.add()
        with (
            patch.object(
                TransferLine, "ensure_valid", side_effect=RuntimeError("must not run")
            ),
            patch.object(
                StockTransferConfirmationPolicy,
                "ensure_confirmable",
                side_effect=RuntimeError("must not run"),
            ),
        ):
            for operation in (
                self.add,
                self.change,
                self.remove,
                self.confirm,
                self.cancel,
            ):
                with self.assertRaises(StockTransferVersionConflictError):
                    operation(planned, expected_version=0)

    def test_explicit_times_are_normalized_to_utc_and_never_go_backwards(self) -> None:
        """Каждая операция проверяет aware-время и хронологию; равные моменты допустимы."""
        offset = timezone(timedelta(hours=2))
        transfer = self.create(created_at=self.time.astimezone(offset))
        self.assertEqual(transfer.created_at, self.time)
        later = self.time + timedelta(minutes=1)
        planned = self.add(transfer, updated_at=later.astimezone(offset))
        self.assertEqual(planned.updated_at, later)
        for operation in (
            self.add,
            self.change,
            self.remove,
            self.confirm,
            self.cancel,
        ):
            for value in (self.time, self.time.replace(tzinfo=None), None, "now"):
                with self.assertRaises(StockTransferTimeError):
                    operation(planned, updated_at=value)
        self.assertEqual(self.confirm(planned, updated_at=later).updated_at, later)
        for value in (
            None,
            "now",
            self.time.replace(tzinfo=None),
            datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        ):
            with self.assertRaises(StockTransferTimeError):
                self.create(created_at=value)

    def test_restore_preserves_complete_history_without_current_context(self) -> None:
        """Восстановление не требует активных складов, актуального шага или текущего коэффициента пересчёта."""
        historical = self.restore_line(
            planned_qty=QuantityVO(Decimal(100)),
            conversion=replace(self.line.conversion, factor_to_base=Decimal("0.002")),
        )
        transfer = self.restore(
            status=StockTransferStatus.CONFIRMED, lines=(historical,), version=7
        )
        self.assertEqual(self.restore(transfer), transfer)
        self.assertEqual(transfer.lines[0].conversion.factor_to_base, Decimal("0.002"))
        draft = self.restore(transfer, status=StockTransferStatus.DRAFT)
        with self.assertRaises(QuantityConversionMismatchError):
            self.confirm(draft)
        fixed = self.change(
            draft, quantity=QuantityVO(Decimal(50000)), uom=UomCodeVO("G")
        )
        self.assertEqual(fixed.lines[0].planned_qty.value, Decimal(50))
        self.assertEqual(fixed.version, 8)

    def test_old_step_can_be_repaired_or_line_removed_without_revalidating_old_quantity(
        self,
    ) -> None:
        """Новый ввод проверяется отдельно: старый некратный черновик можно исправить или удалить."""
        legacy = self.restore_line(
            planned_qty=QuantityVO(Decimal("1.23")),
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal("1.23")), UomCodeVO("KG"), Decimal(1)
            ),
        )
        planned = self.restore(lines=(legacy,), version=1)
        item = replace(
            self.item.stock_snapshot(), quantity_rules=QuantityRulesVO(Decimal("0.1"))
        )
        with self.assertRaises(QuantityStepError):
            self.confirm(planned, inventory_items=(item,))
        fixed = self.change(
            planned, quantity=QuantityVO(Decimal("1.2")), inventory_item=item
        )
        self.assertEqual(fixed.lines[0].planned_qty.value, Decimal("1.2"))
        self.assertEqual(self.remove(planned).lines, ())

    def test_restore_rejects_invalid_header_status_version_and_children(self) -> None:
        """Restore не исправляет повреждённый собственный состав и не подменяет tuple изменяемым списком."""
        for changes in (
            dict(identifier=uuid4()),
            dict(source_warehouse_id=uuid4()),
            dict(destination_warehouse_id=None),
            dict(owner_id=None),
            dict(status="DRAFT"),
            dict(version=True),
            dict(version=-1),
            dict(version="0"),
            dict(lines=[]),
        ):
            with self.assertRaises(InvalidStockTransferValueError):
                self.restore(**changes)
        with self.assertRaises(InvalidStockTransferLineError):
            self.restore(lines=(None,))
        with self.assertRaises(StockTransferLineConflictError):
            self.restore(lines=(self.line, self.line))
        with self.assertRaises(EmptyStockTransferError):
            self.restore(status=StockTransferStatus.CONFIRMED)
        with self.assertRaises(StockTransferTimeError):
            self.restore(updated_at=self.time - timedelta(seconds=1))

    def test_restore_line_rejects_own_type_dimension_and_saved_equality_corruption(
        self,
    ) -> None:
        """Исторический коэффициент допустим, но неверные ссылки, ноль и нарушенное равенство — нет."""
        for changes in (
            dict(identifier=uuid4()),
            dict(inventory_item_id=None),
            dict(base_uom="KG"),
            dict(planned_qty=QuantityVO(Decimal(0))),
            dict(conversion=None),
        ):
            with self.assertRaises(InvalidStockTransferLineError):
                self.restore_line(**changes)
        with self.assertRaises(QuantityConversionMismatchError):
            self.restore_line(planned_qty=QuantityVO(Decimal(51)))
        with self.assertRaises(IncompatibleUomError):
            self.restore_line(base_uom=UomCodeVO("L"))
        with self.assertRaises(UnknownUomError):
            self.restore_line(base_uom=UomCodeVO("UNKNOWN"))

    def test_serial_modes_require_whole_pcs_but_allow_many_planned_instances(
        self,
    ) -> None:
        """SERIAL/LOT_AND_SERIAL допускают план 12 PCS, дробь отвергается без необходимости выбирать экземпляры."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = replace(
                self.item.stock_snapshot(),
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
            )
            line = self.new_line(
                quantity=QuantityVO(Decimal(12)),
                uom=UomCodeVO("PCS"),
                inventory_item=item,
            )
            confirmed = self.confirm(
                self.add(line=line, inventory_item=item), inventory_items=(item,)
            )
            self.assertEqual(confirmed.lines[0].planned_qty.value, Decimal(12))
            with self.assertRaises(QuantityStepError):
                self.new_line(
                    quantity=QuantityVO(Decimal("0.5")),
                    uom=UomCodeVO("PCS"),
                    inventory_item=item,
                )
            for bad in (
                replace(item, base_uom=UomCodeVO("KG")),
                replace(item, quantity_rules=QuantityRulesVO(Decimal("0.5"))),
            ):
                with self.assertRaises(InvalidTrackingConfigurationError):
                    self.new_line(inventory_item=bad)

    def test_lot_required_expiration_does_not_require_lots_or_dates_at_planning(
        self,
    ) -> None:
        """Требования годности не превращают план перемещения в фактическую строку с партией или адресом."""
        item = replace(
            self.item,
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        line = self.new_line(inventory_item=item.stock_snapshot())
        confirmed = self.confirm(
            self.add(line=line, inventory_item=item.stock_snapshot()),
            inventory_items=(item.stock_snapshot(),),
        )
        self.assertEqual(confirmed.status, StockTransferStatus.CONFIRMED)

    def test_different_dimensions_reuse_system_conversions_and_current_quantity_rules(
        self,
    ) -> None:
        """Количество, масса, жидкость, длина и площадь используют одну модель без индивидуальных множителей."""
        for base, unit, value, expected in (
            ("PCS", "PCS", "12", "12"),
            ("KG", "G", "50000", "50"),
            ("L", "ML", "2500", "2.5"),
            ("M3", "L", "2500", "2.5"),
            ("M", "CM", "250", "2.5"),
            ("M2", "DM2", "250", "2.5"),
        ):
            item = replace(self.item.stock_snapshot(), base_uom=UomCodeVO(base))
            line = self.new_line(
                inventory_item=item,
                quantity=QuantityVO(Decimal(value)),
                uom=UomCodeVO(unit),
            )
            transfer = self.confirm(
                self.add(line=line, inventory_item=item), inventory_items=(item,)
            )
            self.assertEqual(transfer.lines[0].planned_qty.value, Decimal(expected))

    def test_mixed_items_require_exact_context_without_combining_or_summing_dimensions(
        self,
    ) -> None:
        """Два разных товара с KG и L сохраняют независимые планы и требуют по одному снимку каждого товара."""
        oil = replace(
            self.item.stock_snapshot(),
            inventory_item_id=InventoryItemIdVO(uuid4()),
            base_uom=UomCodeVO("L"),
        )
        line = self.new_line(
            inventory_item=oil, quantity=QuantityVO(Decimal(2500)), uom=UomCodeVO("ML")
        )
        planned = self.add(self.add(), line, inventory_item=oil)
        confirmed = self.confirm(
            planned, inventory_items=(oil, self.item.stock_snapshot())
        )
        self.assertEqual(
            tuple(line.planned_qty.value for line in confirmed.lines),
            (Decimal(50), Decimal("2.5")),
        )
        with self.assertRaises(InvalidStockTransferContextError):
            self.confirm(planned)

    def test_decimal_context_does_not_round_conversion_or_quantity_checks(self) -> None:
        """Внешний малый контекст и ловушки округления не меняют сохранённый пересчёт или проверку шага."""
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            line = self.new_line(
                quantity=QuantityVO(Decimal(123450)), uom=UomCodeVO("G")
            )
            confirmed = self.confirm(self.add(line=line))
            self.assertEqual(confirmed.lines[0].planned_qty.value, Decimal("123.45"))

    def test_quantity_guard_returns_controlled_error_for_unrepresentable_conversion(
        self,
    ) -> None:
        """Выход за диапазон Decimal при пересчёте передаётся контролируемой ошибкой без округления."""
        item = replace(self.item.stock_snapshot(), base_uom=UomCodeVO("G"))
        with self.assertRaises(UomConversionError):
            self.new_line(
                quantity=QuantityVO(Decimal((0, (1,), MAX_EMAX))), inventory_item=item
            )

    def test_confirmation_policy_direct_use_rejects_bad_composition_and_context(
        self,
    ) -> None:
        """Policy повторно проверяет типы и уникальность даже при вызове без корня агрегата."""
        context = dict(
            source_warehouse_id=self.source.id,
            destination_warehouse_id=self.destination.id,
            source_warehouse=self.source,
            destination_warehouse=self.destination,
            lines=(self.line,),
            inventory_items=(self.item.stock_snapshot(),),
        )
        for changes, error in (
            (dict(lines=[]), InvalidStockTransferLineError),
            (dict(lines=(None,)), InvalidStockTransferLineError),
            (dict(lines=(self.line, self.line)), StockTransferLineConflictError),
            (dict(source_warehouse_id=uuid4()), InvalidStockTransferContextError),
        ):
            with self.assertRaises(error):
                StockTransferConfirmationPolicy.ensure_confirmable(
                    **(context | changes)
                )

    def test_line_policy_direct_use_rejects_untyped_inputs_and_mismatched_current_values(
        self,
    ) -> None:
        """Собственные типы и сохранённый пересчёт не обходятся передачей отдельных аргументов Policy."""
        context = dict(
            inventory_item_id=self.item.id,
            base_uom=self.line.base_uom,
            planned_qty=self.line.planned_qty,
            conversion=self.line.conversion,
            inventory_item=self.item.stock_snapshot(),
        )
        for changes in (
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(planned_qty=QuantityVO(Decimal(0))),
            dict(conversion=None),
        ):
            with self.assertRaises(InvalidStockTransferLineError):
                StockTransferLinePolicy.ensure_compatible(**(context | changes))
        with self.assertRaises(QuantityConversionMismatchError):
            StockTransferLinePolicy.ensure_compatible(
                **(context | dict(planned_qty=QuantityVO(Decimal(100))))
            )

    def test_malformed_direct_construction_cannot_bypass_root_transition_validation(
        self,
    ) -> None:
        """Публичные переходы повторно проверяют собственный состав независимо от способа создания dataclass."""
        transfer = replace(self.create(), lines=[self.line])
        with self.assertRaises(InvalidStockTransferValueError):
            self.cancel(transfer)
        bad_line = replace(self.line, planned_qty=QuantityVO(Decimal(100)))
        with self.assertRaises(QuantityConversionMismatchError):
            self.cancel(replace(self.create(), lines=(bad_line,)))

    def test_success_and_failure_keep_original_objects_unchanged(self) -> None:
        """Подтверждение, отмена и отказ возвращают кандидаты без изменения исходных складов, товара и плана."""
        planned = self.add()
        original = (planned, self.source, self.destination, self.item)
        confirmed = self.confirm(planned)
        cancelled = self.cancel(planned)
        with self.assertRaises(WarehouseInactiveError):
            self.confirm(
                planned,
                destination_warehouse=replace(self.destination, is_active=False),
            )
        self.assertEqual((planned, self.source, self.destination, self.item), original)
        self.assertIs(confirmed.lines, planned.lines)
        self.assertIs(cancelled.lines, planned.lines)
        self.assertEqual(planned.status, StockTransferStatus.DRAFT)


if __name__ == "__main__":
    unittest.main()
