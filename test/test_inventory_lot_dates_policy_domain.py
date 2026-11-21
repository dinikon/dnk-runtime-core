"""Единственный источник дат в партии для доступности, исполнения и новых проводок."""

import unittest
from dataclasses import replace
from datetime import date
from uuid import uuid4

from test import test_inventory_execution_posting_domain as execution_fixture
from test import test_inventory_stock_posting_domain as posting_fixture
from src.modules.inventory.domain.error import ExpirationDateRequiredError
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidTrackingConfigurationError,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_tracking_dates import (
    StockTrackingDatesPolicy,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import StockLotItemMismatchError
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.value_object.lot_number import LotNumberVO
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.error import InvalidPostingContextError
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.serial_number import (
    SerialNumberVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


class LotDatesPostingDomainTests(unittest.TestCase):
    """Проверяет актуальные партии в обоих публичных способах обычного проведения."""

    def setUp(self) -> None:
        """Готовит партийный товар с обязательным сроком и физическую позицию."""
        self.f = posting_fixture.StockPostingDomainTests()
        self.f.setUp()
        self.item = replace(
            self.f.item,
            tracking_mode=TrackingMode.LOT,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        self.lot = StockLot.create(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=self.item.tracking_snapshot(),
            number=LotNumberVO("000Lot-a"),
            dates=StockDatesVO(),
        )
        self.position = replace(
            self.f.first,
            dimensions=replace(self.f.first.dimensions, lot_id=self.lot.id),
        )

    def posting(self, **changes: object) -> StockPosting:
        """Создаёт проводку по явно переданным текущим настройкам и партии."""
        return self.f.posting(
            **(
                dict(
                    entries=(self.f.entry(position=self.position),),
                    positions=(self.position.snapshot(),),
                    inventory_items=(self.item.tracking_snapshot(),),
                    lots=(self.lot.snapshot(),),
                    serials=(),
                )
                | changes
            )
        )

    def from_execution(self, **changes: object) -> StockPosting:
        """Проводит ранее сформированное исполнение с повторной проверкой текущих дат."""
        e = execution_fixture.ExecutionPostingDomainTests()
        e.setUp()
        execution = e.execution(
            lines=(e.line("1", self.position, item=self.item),),
            warehouse_id=self.f.warehouse.id,
            owner_id=self.position.dimensions.owner_id,
        )
        return StockPosting.create_from_execution(
            **(
                dict(
                    identifier=StockPostingIdVO(uuid4()),
                    execution=execution.posting_snapshot(),
                    posted_at=e.time,
                    positions=(self.position.snapshot(),),
                    locations=(self.f.first_location,),
                    entry_bindings=(
                        StockPostingEntryBindingVO(
                            self.position.id, StockLedgerEntryIdVO(uuid4())
                        ),
                    ),
                    inventory_items=(self.item.tracking_snapshot(),),
                    lots=(self.lot.snapshot(),),
                    serials=(),
                )
                | changes
            )
        )

    def test_receipt_requires_expiration_in_both_factories(self) -> None:
        """Существующее исполнение не позволяет обойти обязательный срок партии."""
        for factory in (self.posting, self.from_execution):
            with (
                self.subTest(factory=factory),
                self.assertRaises(ExpirationDateRequiredError),
            ):
                factory()
        self.lot = self.lot.change_dates(
            StockDatesVO(expires_on=date(2027, 1, 1)),
            inventory_item=self.item.tracking_snapshot(),
        )
        for factory in (self.posting, self.from_execution):
            self.assertIsInstance(factory(), StockPosting)
        self.lot = self.lot.change_dates(
            StockDatesVO(), inventory_item=self.item.tracking_snapshot()
        )
        with self.assertRaises(ExpirationDateRequiredError):
            self.from_execution()

    def test_missing_extra_duplicate_and_foreign_context_is_rejected(self) -> None:
        """Проведение требует ровно участвующие настройки и партии без фиктивных подстановок."""
        self.lot = self.lot.change_dates(
            StockDatesVO(expires_on=date(2027, 1, 1)),
            inventory_item=self.item.tracking_snapshot(),
        )
        for changes in (
            dict(inventory_items=()),
            dict(
                inventory_items=(
                    self.item.tracking_snapshot(),
                    self.item.tracking_snapshot(),
                )
            ),
            dict(lots=(self.lot.snapshot(), self.lot.snapshot())),
            dict(
                lots=(
                    self.lot.snapshot(),
                    replace(self.lot.snapshot(), id=StockLotIdVO(uuid4())),
                )
            ),
        ):
            for factory in (self.posting, self.from_execution):
                with (
                    self.subTest(changes=changes, factory=factory),
                    self.assertRaises(InvalidPostingContextError),
                ):
                    factory(**changes)
        with self.assertRaises(StockLotItemMismatchError):
            self.posting(
                lots=(
                    replace(
                        self.lot.snapshot(),
                        inventory_item_id=InventoryItemIdVO(uuid4()),
                    ),
                )
            )

    def test_current_required_configuration_without_lot_is_rejected(self) -> None:
        """Ручной снимок не позволяет обойти новую матрицу SERIAL и обязательного срока."""
        for factory in (self.posting, self.from_execution):
            with (
                self.subTest(factory=factory),
                self.assertRaises(InvalidTrackingConfigurationError),
            ):
                factory(
                    inventory_items=(
                        replace(
                            self.item.tracking_snapshot(),
                            tracking_mode=TrackingMode.SERIAL,
                        ),
                    )
                )

    def test_issue_and_move_do_not_invent_global_expiry_ban(self) -> None:
        """REQUIRED требует срок при поступлении, не препятствуя учёту расхода и перемещения."""
        self.assertIsInstance(
            self.posting(
                operation_type=StockOperationType.ISSUE,
                entries=(self.f.entry("-1", self.position),),
            ),
            StockPosting,
        )
        destination = replace(
            self.f.second,
            dimensions=replace(self.f.second.dimensions, lot_id=self.lot.id),
        )
        self.assertIsInstance(
            self.posting(
                operation_type=StockOperationType.INTERNAL_MOVE,
                entries=(
                    self.f.entry("-1", self.position),
                    self.f.entry("1", destination),
                ),
                positions=(self.position.snapshot(), destination.snapshot()),
                locations=(self.f.first_location, self.f.second_location),
            ),
            StockPosting,
        )
        self.lot = self.lot.change_dates(
            StockDatesVO(expires_on=date(2000, 1, 1)),
            inventory_item=self.item.tracking_snapshot(),
        )
        self.assertIsInstance(self.posting(), StockPosting)

    def test_history_and_reversal_need_no_current_lot_dates(self) -> None:
        """Очистка текущих дат партии не переписывает историю и не запрещает точное сторно."""
        self.lot = self.lot.change_dates(
            StockDatesVO(expires_on=date(2027, 1, 1)),
            inventory_item=self.item.tracking_snapshot(),
        )
        posting = self.posting()
        self.lot = self.lot.change_dates(
            StockDatesVO(), inventory_item=self.item.tracking_snapshot()
        )
        self.assertEqual(self.f.restore(posting), posting)
        reverse = self.f.reverse(posting, positions=(self.position.snapshot(),))
        self.assertEqual(
            reverse.entries[0].quantity_delta.value,
            -posting.entries[0].quantity_delta.value,
        )
        self.assertEqual(reverse.reversal_of_id, posting.id)
        self.assertNotIn("dates", posting.__dataclass_fields__)

    def test_lot_and_serial_resolve_only_the_linked_lot(self) -> None:
        """Серийная ссылка выбирает дату партии и не хранит её копию."""
        item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("S"),
            tracking_mode=TrackingMode.LOT_AND_SERIAL,
            expiration_mode=ExpirationMode.REQUIRED,
        )
        lot = StockLot.create(
            identifier=StockLotIdVO(uuid4()),
            inventory_item=item.tracking_snapshot(),
            number=LotNumberVO("L"),
            dates=StockDatesVO(expires_on=date(2027, 1, 1)),
        )
        serial = StockSerial.create(
            identifier=StockSerialIdVO(uuid4()),
            inventory_item=item.tracking_snapshot(),
            number=SerialNumberVO("000SN-a"),
            lot=lot.snapshot(),
        )
        self.assertIs(
            StockTrackingDatesPolicy.resolve(
                inventory_item=item.tracking_snapshot(),
                lot_id=lot.id,
                lot=lot.snapshot(),
                serial=serial.snapshot(),
            ),
            lot.dates,
        )
