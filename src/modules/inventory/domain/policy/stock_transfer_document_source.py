from typing import ClassVar
from uuid import UUID

from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentError,
    InvalidStockDocumentLineError,
    StockDocumentTransferDispatchMismatchError,
    StockDocumentTransferReceiptMismatchError,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)


class StockTransferDocumentSourcePolicy:
    """Проверяет собственную структуру оснований документов двух этапов без актуального StockTransfer."""

    DISPATCH_ISSUE_SYSTEM: ClassVar[str] = "inventory.stock_transfer.dispatch_issue"
    DISPATCH_RECEIPT_SYSTEM: ClassVar[str] = "inventory.stock_transfer.dispatch_receipt"
    RECEIPT_ISSUE_SYSTEM: ClassVar[str] = "inventory.stock_transfer.receipt_issue"
    RECEIPT_RECEIPT_SYSTEM: ClassVar[str] = "inventory.stock_transfer.receipt_receipt"
    LINE_SOURCE_SYSTEM: ClassVar[str] = "inventory.stock_transfer_line"

    @staticmethod
    def ensure_document_source(
        *,
        operation_type: StockOperationType,
        source: DocumentSourceVO | None,
        lines: tuple[StockDocumentLine, ...],
    ) -> None:
        """Требует правильную роль, версию, канонические UUID и уникальные основания строк для обоих этапов."""
        if (
            source is not None and not isinstance(source, DocumentSourceVO)
        ) or not isinstance(lines, tuple):
            raise StockDocumentTransferDispatchMismatchError(
                "Некорректные основание или состав документа перемещения."
            )
        roles = {
            StockTransferDocumentSourcePolicy.DISPATCH_ISSUE_SYSTEM: StockOperationType.ISSUE,
            StockTransferDocumentSourcePolicy.DISPATCH_RECEIPT_SYSTEM: StockOperationType.RECEIPT,
            StockTransferDocumentSourcePolicy.RECEIPT_ISSUE_SYSTEM: StockOperationType.ISSUE,
            StockTransferDocumentSourcePolicy.RECEIPT_RECEIPT_SYSTEM: StockOperationType.RECEIPT,
        }
        linked = source is not None and source.system in roles
        receipt_phase = source is not None and source.system in (
            StockTransferDocumentSourcePolicy.RECEIPT_ISSUE_SYSTEM,
            StockTransferDocumentSourcePolicy.RECEIPT_RECEIPT_SYSTEM,
        )
        error_type = (
            StockDocumentTransferReceiptMismatchError
            if receipt_phase
            else StockDocumentTransferDispatchMismatchError
        )
        if linked:
            if operation_type is not roles[source.system] or source.version is None:
                raise error_type(
                    "Роль основания должна соответствовать операции и содержать версию."
                )
            StockTransferDocumentSourcePolicy._ensure_reference(
                source.reference, error_type
            )
        refs = set()
        for line in lines:
            if not isinstance(line, StockDocumentLine):
                raise InvalidStockDocumentLineError("Нужны строки StockDocumentLine.")
            line.ensure_valid()
            if linked:
                if (
                    line.source is None
                    or line.source.system
                    != StockTransferDocumentSourcePolicy.LINE_SOURCE_SYSTEM
                ):
                    raise error_type("Каждая строка должна ссылаться на TransferLine.")
                StockTransferDocumentSourcePolicy._ensure_reference(
                    line.source.reference, error_type
                )
                if line.source.reference in refs:
                    raise error_type("Основания строк не должны повторяться.")
                refs.add(line.source.reference)
            elif (
                line.source is not None
                and line.source.system
                == StockTransferDocumentSourcePolicy.LINE_SOURCE_SYSTEM
            ):
                raise error_type(
                    "Основание TransferLine требует шапку одного из этапов StockTransfer."
                )

    @staticmethod
    def _ensure_reference(reference: str, error_type: type[StockDocumentError]) -> None:
        """Проверяет канонический UUID с ошибкой соответствующего этапа, не нормализуя внешние ссылки."""
        try:
            identifier = UUID(reference)
        except (ValueError, TypeError, AttributeError) as exc:
            raise error_type("Основание перемещения должно содержать UUID.") from exc
        if str(identifier) != reference:
            raise error_type(
                "UUID основания должен иметь каноническую строковую форму."
            )
