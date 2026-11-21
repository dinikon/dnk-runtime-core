"""Самостоятельные инварианты STATUS_CHANGE и сохранение идентичности физического запаса."""

from dataclasses import replace
from uuid import uuid4
from decimal import Decimal
import unittest
from test.test_inventory_execution_posting_domain import (
    ExecutionPostingDomainTests as Support,
)
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.stock_document.value_object.status_change_details import (
    StockStatusChangeDetailsVO,
)
from src.modules.inventory.domain.stock_document.value_object.status_change_reason import (
    StatusChangeReasonVO,
)
from src.modules.inventory.domain.policy.stock_status_transition import (
    StockStatusTransitionPolicy,
)
from src.modules.inventory.domain.stock_execution.value_object.status_change_route import (
    StatusChangeExecutionRouteVO,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    InvalidStockStatusChangeError,
    StockStatusChangeBalanceError,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionRouteError,
    InvalidStockExecutionPostingSnapshotError,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotDraftError,
    InvalidStockDocumentContextError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.policy.stock_status_change_balance import (
    StockStatusChangeBalancePolicy,
)


class StatusChangeDomainTests(unittest.TestCase):
    """Проверяет бизнес-правила независимо от SQL и HTTP."""

    def setUp(self) -> None:
        """Создаёт чистые фикстуры товара, адресов и подписанного маршрута."""
        self.f = Support()
        self.f.setUp()
        self.details = StockStatusChangeDetailsVO(
            StockStatus.QUARANTINE, StatusChangeReasonVO("Контроль качества")
        )
        self.source = self.f.a
        self.destination = replace(
            self.source,
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(
                self.source.dimensions, stock_status=StockStatus.QUARANTINE
            ),
        )

    def execution(self) -> StockExecution:
        """Восстанавливает согласованный фактический переход с отдельными реквизитами."""
        line = self.f.line(
            route=StatusChangeExecutionRouteVO(
                self.source.dimensions, self.destination.dimensions
            )
        )
        return self.f.execution(
            (line,),
            kind=StockOperationType.STATUS_CHANGE,
            status_change_details=self.details,
        )

    def posting(self) -> StockPosting:
        """Строит две записи Ledger через проверенный снимок исполнения."""
        return self.f.posting(
            self.execution(),
            positions=(self.source.snapshot(), self.destination.snapshot()),
            entry_bindings=tuple(
                StockPostingEntryBindingVO(p.id, StockLedgerEntryIdVO(uuid4()))
                for p in (self.source, self.destination)
            ),
        )

    def document(self) -> StockDocument:
        """Создаёт и подтверждает независимый документ смены состояния."""
        document = StockDocument.create(
            identifier=StockDocumentIdVO(uuid4()),
            operation_type=StockOperationType.STATUS_CHANGE,
            warehouse=self.f.warehouse,
            owner_id=self.f.owner,
            created_at=self.f.time,
            status_change_details=self.details,
        )
        document = document.add_line(
            StockDocumentLine.create(
                identifier=self.f.document_line_id,
                inventory_item=self.f.item.document_snapshot(),
                quantity=QuantityVO(Decimal(2)),
                uom=self.f.item.base_uom,
            ),
            inventory_item=self.f.item.document_snapshot(),
            updated_at=self.f.time,
        )
        return document.confirm(
            warehouse=self.f.warehouse,
            inventory_items=(self.f.item.document_snapshot(),),
            updated_at=self.f.time,
        )

    def test_matrix_has_twelve_directed_transitions(self) -> None:
        """Все различающиеся состояния разрешены, каждый переход в себя запрещён."""
        for source in StockStatus:
            self.assertEqual(
                len(StockStatusTransitionPolicy.allowed_targets(source)), 3
            )
            for target in StockStatus:
                with self.subTest(source=source, target=target):
                    if source is target:
                        with self.assertRaises(InvalidStockStatusChangeError):
                            StockStatusTransitionPolicy.ensure_allowed(source, target)
                    else:
                        StockStatusTransitionPolicy.ensure_allowed(source, target)

    def test_route_preserves_every_other_dimension(self) -> None:
        """Под видом состояния нельзя заменить адрес, владельца, SKU или LOT/SERIAL."""
        valid = StatusChangeExecutionRouteVO.to_status(
            self.source.dimensions, StockStatus.BLOCKED
        )
        self.assertEqual(
            replace(valid.source, stock_status=StockStatus.BLOCKED), valid.destination
        )
        for dims in (
            replace(valid.destination, location_id=self.f.locations[1].id),
            replace(valid.destination, owner_id=type(self.f.owner)(uuid4())),
            replace(valid.destination, inventory_item_id=type(self.f.item.id)(uuid4())),
        ):
            with self.assertRaises(InvalidStockExecutionRouteError):
                StatusChangeExecutionRouteVO(valid.source, dims)

    def test_details_are_mandatory_and_target_matches_every_line(self) -> None:
        """Операции нужен собственный реквизит; маршрут обязан соответствовать замороженной цели."""
        execution = self.execution()
        for details in (None, replace(self.details, target_status=StockStatus.DAMAGED)):
            with self.assertRaises(
                (InvalidStockStatusChangeError, InvalidStockExecutionRouteError)
            ):
                replace(execution, status_change_details=details).posting_snapshot()
        with self.assertRaises(InvalidStockStatusChangeError):
            self.f.execution(status_change_details=self.details)

    def test_balanced_posting_debits_and_credits_equal_quantity(self) -> None:
        """Общий запас сохраняется, проводка содержит обе стороны одной локации."""
        posting = self.posting()
        self.assertEqual(
            sorted(e.quantity_delta.value for e in posting.entries),
            [Decimal(-2), Decimal(2)],
        )
        self.assertEqual(
            sum(e.quantity_delta.value for e in posting.entries), Decimal(0)
        )

    def test_balance_cannot_hide_location_change(self) -> None:
        """Проверка баланса по складу не позволяет подменить смену состояния перемещением."""
        posting = self.posting()
        altered = replace(
            self.destination,
            dimensions=replace(
                self.destination.dimensions, location_id=self.f.locations[1].id
            ),
        )
        with self.assertRaises(StockStatusChangeBalanceError):
            StockStatusChangeBalancePolicy.ensure_balanced(
                entries=posting.entries,
                positions=(self.source.snapshot(), altered.snapshot()),
                locations=self.f.locations[:2],
            )

    def test_direct_factory_cannot_bypass_execution(self) -> None:
        """Низкоуровневое создание проведения не обходит причину, цель и маршруты исполнения."""
        posting = self.posting()
        with self.assertRaises(InvalidStockExecutionPostingSnapshotError):
            StockPosting.create(
                identifier=posting.id,
                source=posting.source,
                operation_type=StockOperationType.STATUS_CHANGE,
                posted_at=posting.posted_at,
                entries=posting.entries,
                positions=(self.source.snapshot(), self.destination.snapshot()),
                locations=(self.f.locations[0],),
            )

    def test_confirmed_details_immutable_and_registration_compares_snapshot(
        self,
    ) -> None:
        """Подтверждённая цель и основание не редактируются и сверяются при регистрации факта."""
        document = self.document()
        with self.assertRaises(StockDocumentNotDraftError):
            document.change_status_change_details(
                replace(self.details, target_status=StockStatus.BLOCKED),
                updated_at=self.f.time,
            )
        snapshot = replace(
            self.execution().snapshot_for_document(),
            document_id=document.id,
            document_version=document.version,
            status_change_details=replace(
                self.details, reason=StatusChangeReasonVO("Другое основание")
            ),
        )
        with self.assertRaises(InvalidStockDocumentContextError):
            document.register_execution(snapshot, updated_at=self.f.time)
