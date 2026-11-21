"""Самостоятельные правила WRITE_OFF и неизменяемая причина фактического списания."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4
import unittest
from test.test_inventory_execution_posting_domain import (
    ExecutionPostingDomainTests as Support,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.write_off_reason import (
    WriteOffReasonVO,
)
from src.modules.inventory.domain.stock_document.write_off_error import (
    InvalidWriteOffReasonError,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotDraftError,
    InvalidStockDocumentContextError,
)
from src.modules.inventory.domain.stock_execution.value_object.write_off_route import (
    WriteOffExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionRouteError,
    InvalidStockExecutionValueError,
    InvalidStockExecutionPostingSnapshotError,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.error import StockPostingSignError
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class WriteOffDomainTests(unittest.TestCase):
    """Проверяет бизнес-правила без SQL, HTTP и текущих внешних справочников."""

    def setUp(self) -> None:
        """Создаёт чистые снимки и идентичности существующего учётного Domain."""
        self.f = Support()
        self.f.setUp()
        self.reason = WriteOffReasonVO("Повреждение упаковки")

    def document(self, reason: WriteOffReasonVO | None = None) -> StockDocument:
        """Готовит подтверждённый план на 10 KG с обязательным основанием."""
        f = self.f
        document = StockDocument.create(
            identifier=StockDocumentIdVO(uuid4()),
            operation_type=StockOperationType.WRITE_OFF,
            warehouse=f.warehouse,
            owner_id=f.owner,
            created_at=f.time,
            write_off_reason=reason or self.reason,
        )
        document = document.add_line(
            StockDocumentLine.create(
                identifier=f.document_line_id,
                inventory_item=f.item.document_snapshot(),
                quantity=QuantityVO(Decimal(10)),
                uom=f.item.base_uom,
            ),
            inventory_item=f.item.document_snapshot(),
            updated_at=f.time,
        )
        return document.confirm(
            warehouse=f.warehouse,
            inventory_items=(f.item.document_snapshot(),),
            updated_at=f.time,
        )

    def execution(self) -> StockExecution:
        """Создаёт фактическое списание по подтверждённому плану с копией причины."""
        f = self.f
        document = self.document()
        return StockExecution.create(
            identifier=f.execution().id,
            document=document.execution_snapshot(),
            executed_at=f.time,
            lines=(f.line(route=WriteOffExecutionRouteVO(f.a.dimensions)),),
            warehouse=f.warehouse,
            inventory_items=(f.item.execution_snapshot(),),
            locations=(f.locations[0],),
        )

    def test_reason_normalization_and_invalid_values(self) -> None:
        """Причина сохраняет содержимое и регистр, но не допускает пустой текст и недопустимые знаки."""
        self.assertEqual(
            WriteOffReasonVO("  Потери\nПри пересчёте  ").value, "Потери\nПри пересчёте"
        )
        for value in ["", "   ", "x" * 1001, "текст\x00"]:
            with (
                self.subTest(value=value[:20]),
                self.assertRaises(InvalidWriteOffReasonError),
            ):
                WriteOffReasonVO(value)

    def test_document_requires_reason_and_freezes_it_on_confirmation(self) -> None:
        """Причина обязательна именно для WRITE_OFF и не меняется после фиксации плана."""
        f = self.f
        with self.assertRaises(InvalidWriteOffReasonError):
            StockDocument.create(
                identifier=f.document_id,
                operation_type=StockOperationType.WRITE_OFF,
                warehouse=f.warehouse,
                owner_id=f.owner,
                created_at=f.time,
            )
        with self.assertRaises(InvalidWriteOffReasonError):
            StockDocument.create(
                identifier=f.document_id,
                operation_type=StockOperationType.ISSUE,
                warehouse=f.warehouse,
                owner_id=f.owner,
                created_at=f.time,
                write_off_reason=self.reason,
            )
        document = self.document()
        with self.assertRaises(StockDocumentNotDraftError):
            document.change_write_off_reason(
                WriteOffReasonVO("Другая причина"), updated_at=f.time
            )

    def test_execution_and_posting_keep_distinct_type_and_reason(self) -> None:
        """Исполнение сохраняет причину, а проведение формирует только отрицательный Ledger типа WRITE_OFF."""
        execution = self.execution()
        self.assertEqual(execution.write_off_reason, self.reason)
        self.assertEqual(execution.posting_snapshot().write_off_reason, self.reason)
        posting = self.f.posting(execution)
        self.assertEqual(posting.operation_type, StockOperationType.WRITE_OFF)
        self.assertEqual(posting.entries[0].quantity_delta.value, Decimal(-2))

    def test_reason_cannot_be_removed_from_stored_fact_or_posting_snapshot(
        self,
    ) -> None:
        """Полное восстановление и снимок проведения не принимают WRITE_OFF без основания."""
        execution = self.execution()
        with self.assertRaises(InvalidWriteOffReasonError):
            replace(execution, write_off_reason=None).posting_snapshot()
        with self.assertRaises(InvalidWriteOffReasonError):
            replace(execution.posting_snapshot(), write_off_reason=None).ensure_valid()
        with self.assertRaises(InvalidWriteOffReasonError):
            replace(
                execution.snapshot_for_document(), write_off_reason=None
            ).ensure_valid()

    def test_document_rejects_execution_with_another_reason(self) -> None:
        """Регистрация повторно сверяет неизменяемое основание с текущим подтверждённым планом."""
        document = self.document()
        execution = self.execution()
        snapshot = replace(
            execution.snapshot_for_document(),
            document_id=document.id,
            document_version=document.version,
            write_off_reason=WriteOffReasonVO("Другое основание"),
        )
        with self.assertRaises(InvalidStockDocumentContextError):
            document.register_execution(snapshot, updated_at=self.f.time)

    def test_direct_posting_factory_cannot_skip_validated_execution(self) -> None:
        """Низкоуровневая фабрика не создаёт WRITE_OFF по одному только ID основания."""
        posting = self.f.posting(self.execution())
        with self.assertRaises(InvalidStockExecutionPostingSnapshotError):
            StockPosting.create(
                identifier=posting.id,
                source=posting.source,
                operation_type=StockOperationType.WRITE_OFF,
                posted_at=posting.posted_at,
                entries=posting.entries,
                positions=(self.f.a.snapshot(),),
            )
        positive = replace(
            posting.entries[0],
            quantity_delta=self.f.posting().entries[0].quantity_delta,
        )
        with self.assertRaises(StockPostingSignError):
            StockPosting.restore(
                identifier=posting.id,
                source=posting.source,
                operation_type=StockOperationType.WRITE_OFF,
                posted_at=posting.posted_at,
                entries=(positive,),
                reversal_of_id=None,
            )

    def test_issue_route_does_not_masquerade_as_write_off(self) -> None:
        """Отдельный тип требует собственного расходного маршрута."""
        with self.assertRaises(
            (InvalidStockExecutionValueError, InvalidStockExecutionRouteError)
        ):
            self.f.execution(
                (self.f.line(),),
                kind=StockOperationType.WRITE_OFF,
                write_off_reason=self.reason,
            )
