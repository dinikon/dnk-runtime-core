"""Предусловия ручного жизненного цикла не зависят от Application и HTTP."""

import unittest
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentValueError,
    StaleStockDocumentVersionError,
    InvalidStockDocumentContextError,
    StockDocumentNotDraftError,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from test import test_inventory_stock_document_domain as support


class ReceiptLifecycleDomainTests(unittest.TestCase):
    """Проверяет общие защитные методы агрегата для новых команд."""

    def setUp(self) -> None:
        """Создаёт полноценную Domain-фикстуру без SQL и системного времени."""
        self.fixture = support.StockDocumentDomainTests()
        self.fixture.setUp()

    def test_expected_version_is_strict_and_reports_both_versions(self) -> None:
        """Bool и отрицательные версии недопустимы; конфликт хранит исходную и текущую версии."""
        document = self.fixture.planned
        document.ensure_version(1)
        for value in (True, -1):
            with self.assertRaises(InvalidStockDocumentValueError):
                document.ensure_version(value)
        with self.assertRaises(StaleStockDocumentVersionError) as caught:
            document.ensure_version(0)
        self.assertEqual(
            (caught.exception.expected_version, caught.exception.actual_version), (0, 1)
        )
        self.assertEqual(document.version, 1)

    def test_manual_receipt_rejects_other_operations_and_derived_sources(self) -> None:
        """Ручные команды не обслуживают расходы и планы, принадлежащие внешнему основанию."""
        self.fixture.document.ensure_manual_receipt()
        for document in (
            self.fixture.create(operation_type=StockOperationType.ISSUE),
            self.fixture.create(source=DocumentSourceVO("external", "reference")),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                document.ensure_manual_receipt()

    def test_cancelled_empty_plan_cannot_pass_noop_edit(self) -> None:
        """Предусловие редактирования действует даже при пустом запросе строк."""
        cancelled = self.fixture.document.cancel(updated_at=self.fixture.at(1))
        with self.assertRaises(StockDocumentNotDraftError):
            cancelled.ensure_can_edit_lines()
