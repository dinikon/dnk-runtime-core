from datetime import datetime, timedelta
from typing import ClassVar
from uuid import UUID

from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.policy.stock_document_confirmation import (
    StockDocumentConfirmationPolicy,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentLineError,
    InvalidStockDocumentTransferDispatchSnapshotError,
    InvalidStockTransferDispatchDocumentLineBindingError,
    StockDocumentTransferDispatchMismatchError,
    StaleStockTransferDocumentSourceError,
    StockDocumentTransferDispatchQuantityExceededError,
    UnbalancedStockTransferDispatchDocumentsError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
    StockDocumentNotDraftError,
)
from src.modules.inventory.domain.stock_document.transfer_dispatch_snapshot import (
    StockDocumentTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_document.value_object.transfer_dispatch_line_binding import (
    StockTransferDispatchDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.dispatch_document_snapshot import (
    StockTransferDispatchDocumentSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferDispatchDocumentSnapshotError,
    StockTransferStatusError,
    StockTransferTransitMismatchError,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferDispatchDocumentPolicy:
    """Строит планы отправки A → T и повторно согласует их основания и количества перед подтверждением."""

    ISSUE_SOURCE_SYSTEM: ClassVar[str] = "inventory.stock_transfer.dispatch_issue"
    RECEIPT_SOURCE_SYSTEM: ClassVar[str] = "inventory.stock_transfer.dispatch_receipt"
    LINE_SOURCE_SYSTEM: ClassVar[str] = "inventory.stock_transfer_line"

    @staticmethod
    def source_system(operation_type: StockOperationType) -> str:
        """Выбирает зарезервированную роль документа отправки только для ISSUE или RECEIPT."""
        if operation_type is StockOperationType.ISSUE:
            return StockTransferDispatchDocumentPolicy.ISSUE_SOURCE_SYSTEM
        if operation_type is StockOperationType.RECEIPT:
            return StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM
        raise StockDocumentTransferDispatchMismatchError(
            "Документы отправки поддерживают только ISSUE и RECEIPT."
        )

    @staticmethod
    def build_lines(
        *,
        transfer: StockTransferDispatchDocumentSnapshot,
        operation_type: StockOperationType,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        transit_warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        line_bindings: tuple[StockTransferDispatchDocumentLineBindingVO, ...],
        as_of: datetime,
    ) -> tuple[StockDocumentLine, ...]:
        """Строит одну сторону пары на весь открытый остаток, сохраняя отдельные обязательства одного товара."""
        StockTransferDispatchDocumentPolicy.source_system(operation_type)
        StockTransferDispatchDocumentPolicy._ensure_transfer(transfer, as_of)
        if not isinstance(transit_warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError(
                "Нужен снимок выбранного транзитного склада."
            )
        # Проверяется также роль каждого явно названного склада, а не только совпадение множества ID.
        for warehouse, identifier in (
            (source_warehouse, transfer.source_warehouse_id),
            (destination_warehouse, transfer.destination_warehouse_id),
        ):
            StockDocumentConfirmationPolicy.ensure_warehouse(
                warehouse_id=identifier, warehouse=warehouse
            )
        StockTransferDispatchDocumentPolicy._ensure_warehouses(
            transfer=transfer,
            transit_id=transit_warehouse.id,
            warehouses=(source_warehouse, destination_warehouse, transit_warehouse),
        )
        if not isinstance(inventory_items, tuple):
            raise InvalidStockDocumentContextError(
                "Нужен tuple текущих товарных снимков."
            )
        items = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemDocumentSnapshot):
                raise InvalidInventoryItemDocumentSnapshotError(
                    "Нужны снимки товаров складского документа."
                )
            item.ensure_valid()
            if item.inventory_item_id in items:
                raise InvalidStockDocumentContextError(
                    "Товарные снимки не должны повторяться."
                )
            items[item.inventory_item_id] = item
        if set(items) != {line.inventory_item_id for line in transfer.lines}:
            raise InvalidStockDocumentContextError(
                "Нужны ровно участвующие товарные снимки без пропусков и лишних."
            )
        if not isinstance(line_bindings, tuple):
            raise InvalidStockTransferDispatchDocumentLineBindingError(
                "Назначения ID строк передаются в tuple."
            )
        bindings, ids = {}, set()
        for binding in line_bindings:
            if not isinstance(binding, StockTransferDispatchDocumentLineBindingVO):
                raise InvalidStockTransferDispatchDocumentLineBindingError(
                    "Нужны типизированные назначения ID обеих сторон."
                )
            values = (binding.issue_document_line_id, binding.receipt_document_line_id)
            if binding.transfer_line_id in bindings or ids.intersection(values):
                raise InvalidStockTransferDispatchDocumentLineBindingError(
                    "ID оснований и всех новых строк должны быть уникальны."
                )
            bindings[binding.transfer_line_id] = binding
            ids.update(values)
        if set(bindings) != {line.transfer_line_id for line in transfer.lines}:
            raise InvalidStockTransferDispatchDocumentLineBindingError(
                "Нужно назначить ровно все открытые строки перемещения."
            )
        result = []
        for line in sorted(
            transfer.lines, key=lambda value: value.transfer_line_id.uuid.int
        ):
            item = items[line.inventory_item_id]
            if item.base_uom != line.base_uom:
                raise StockDocumentUomMismatchError(
                    "Текущая базовая единица товара отличается от основания."
                )
            binding = bindings[line.transfer_line_id]
            result.append(
                StockDocumentLine.create(
                    identifier=(
                        binding.issue_document_line_id
                        if operation_type is StockOperationType.ISSUE
                        else binding.receipt_document_line_id
                    ),
                    inventory_item=item,
                    quantity=line.remaining_qty,
                    uom=line.base_uom,
                    source=DocumentLineSourceVO(
                        StockTransferDispatchDocumentPolicy.LINE_SOURCE_SYSTEM,
                        str(line.transfer_line_id.uuid),
                    ),
                )
            )
        return tuple(result)

    @staticmethod
    def ensure_document_source(
        *,
        operation_type: StockOperationType,
        source: DocumentSourceVO | None,
        lines: tuple[StockDocumentLine, ...],
    ) -> None:
        """Проверяет собственную структуру зарезервированных оснований без актуального перемещения или парного документа."""
        if (
            source is not None and not isinstance(source, DocumentSourceVO)
        ) or not isinstance(lines, tuple):
            raise StockDocumentTransferDispatchMismatchError(
                "Некорректные основание или состав документа отправки."
            )
        linked = source is not None and source.system in (
            StockTransferDispatchDocumentPolicy.ISSUE_SOURCE_SYSTEM,
            StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
        )
        if linked:
            if (
                source.system
                != StockTransferDispatchDocumentPolicy.source_system(operation_type)
                or source.version is None
            ):
                raise StockDocumentTransferDispatchMismatchError(
                    "Роль основания должна соответствовать операции и содержать версию."
                )
            StockTransferDispatchDocumentPolicy._ensure_canonical_reference(
                source.reference
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
                    != StockTransferDispatchDocumentPolicy.LINE_SOURCE_SYSTEM
                ):
                    raise StockDocumentTransferDispatchMismatchError(
                        "Каждая строка должна ссылаться на TransferLine."
                    )
                StockTransferDispatchDocumentPolicy._ensure_canonical_reference(
                    line.source.reference
                )
                if line.source.reference in refs:
                    raise StockDocumentTransferDispatchMismatchError(
                        "Основания строк не должны повторяться."
                    )
                refs.add(line.source.reference)
            elif (
                line.source is not None
                and line.source.system
                == StockTransferDispatchDocumentPolicy.LINE_SOURCE_SYSTEM
            ):
                raise StockDocumentTransferDispatchMismatchError(
                    "Основание TransferLine требует шапку документа отправки StockTransfer."
                )

    @staticmethod
    def ensure_confirmable(
        *,
        document: StockDocumentTransferDispatchSnapshot | None,
        companion: StockDocumentTransferDispatchSnapshot | None,
        transfer: StockTransferDispatchDocumentSnapshot | None,
        warehouses: tuple[WarehouseSnapshot, ...] | None,
        as_of: datetime,
    ) -> None:
        """Требует свежую версию основания и согласованный парный план; обычным документам контекст не передаётся."""
        if document is None:
            if companion is not None or transfer is not None or warehouses is not None:
                raise InvalidStockDocumentContextError(
                    "Контекст перемещения передаётся только документам отправки StockTransfer."
                )
            return
        if not isinstance(document, StockDocumentTransferDispatchSnapshot):
            raise InvalidStockDocumentTransferDispatchSnapshotError(
                "Нужен снимок подтверждаемого документа отправки."
            )
        document.ensure_valid()
        if document.status is not StockDocumentStatus.DRAFT:
            raise StockDocumentNotDraftError(
                "Подтверждать можно только черновик документа отправки."
            )
        StockTransferDispatchDocumentPolicy.ensure_pair_compatible(
            first=document,
            second=companion,
            transfer=transfer,
            warehouses=warehouses,
            as_of=as_of,
        )

    @staticmethod
    def ensure_pair_compatible(
        *,
        first: StockDocumentTransferDispatchSnapshot,
        second: StockDocumentTransferDispatchSnapshot,
        transfer: StockTransferDispatchDocumentSnapshot,
        warehouses: tuple[WarehouseSnapshot, ...],
        as_of: datetime,
    ) -> None:
        """Сверяет две разные стороны одного актуального основания, текущие склады и одинаковые планы по каждой строке."""
        StockTransferDispatchDocumentPolicy._ensure_transfer(transfer, as_of)
        for document in (first, second):
            if not isinstance(document, StockDocumentTransferDispatchSnapshot):
                raise InvalidStockDocumentTransferDispatchSnapshotError(
                    "Нужны снимки обеих сторон отправки."
                )
            document.ensure_valid()
            if document.status not in (
                StockDocumentStatus.DRAFT,
                StockDocumentStatus.CONFIRMED,
            ):
                raise StockDocumentNotDraftError(
                    "Сопряжённый документ должен быть черновиком или подтверждённым планом без исполнения."
                )
            if (
                document.transfer_id != transfer.id
                or document.owner_id != transfer.owner_id
            ):
                raise StockDocumentTransferDispatchMismatchError(
                    "Основание и владелец пары должны соответствовать StockTransfer."
                )
            if document.source_transfer_version != transfer.version:
                raise StaleStockTransferDocumentSourceError(
                    "Основание изменилось: перестройте документы по текущей версии перемещения."
                )
            if document.updated_at > as_of:
                raise StockDocumentTimeError(
                    "Подтверждение не может предшествовать состоянию одной из сторон пары."
                )
        if first.id == second.id or {first.operation_type, second.operation_type} != {
            StockOperationType.ISSUE,
            StockOperationType.RECEIPT,
        }:
            raise StockDocumentTransferDispatchMismatchError(
                "Нужны два разных документа ISSUE A и RECEIPT T."
            )
        issue, receipt = (
            (first, second)
            if first.operation_type is StockOperationType.ISSUE
            else (second, first)
        )
        if issue.warehouse_id != transfer.source_warehouse_id:
            raise StockDocumentTransferDispatchMismatchError(
                "Расход пары должен относиться к исходному складу A."
            )
        StockTransferDispatchDocumentPolicy._ensure_warehouses(
            transfer=transfer,
            transit_id=receipt.warehouse_id,
            warehouses=warehouses,
        )
        if {line.document_line_id for line in issue.lines}.intersection(
            line.document_line_id for line in receipt.lines
        ):
            raise StockDocumentTransferDispatchMismatchError(
                "ID плановых строк обеих сторон должны различаться."
            )
        outgoing = {
            line.transfer_line_id: (
                line.inventory_item_id,
                line.base_uom,
                line.planned_qty,
            )
            for line in issue.lines
        }
        incoming = {
            line.transfer_line_id: (
                line.inventory_item_id,
                line.base_uom,
                line.planned_qty,
            )
            for line in receipt.lines
        }
        if not outgoing or outgoing != incoming:
            raise UnbalancedStockTransferDispatchDocumentsError(
                "Планы расхода A и прихода T должны совпадать по каждой строке перемещения."
            )
        plan = {line.transfer_line_id: line for line in transfer.lines}
        for identifier, (item_id, base_uom, quantity) in outgoing.items():
            target = plan.get(identifier)
            if (
                target is None
                or target.inventory_item_id != item_id
                or target.base_uom != base_uom
            ):
                raise StockDocumentTransferDispatchMismatchError(
                    "Строка, товар и единица пары не соответствуют открытому остатку основания."
                )
            if quantity.value > target.remaining_qty.value:
                raise StockDocumentTransferDispatchQuantityExceededError(
                    "План пары превышает текущий остаток строки к отправке."
                )

    @staticmethod
    def _ensure_transfer(
        transfer: StockTransferDispatchDocumentSnapshot, as_of: datetime
    ) -> None:
        """Проверяет снимок, допустимый статус, наличие открытых строк и явное UTC-время решения."""
        if not isinstance(transfer, StockTransferDispatchDocumentSnapshot):
            raise InvalidStockTransferDispatchDocumentSnapshotError(
                "Нужен снимок открытого плана StockTransfer."
            )
        transfer.ensure_valid()
        if transfer.status not in (
            StockTransferStatus.CONFIRMED,
            StockTransferStatus.IN_PROGRESS,
        ):
            raise StockTransferStatusError(
                "Документы отправки строятся и подтверждаются только после подтверждения перемещения."
            )
        if not transfer.lines:
            raise EmptyStockDocumentError(
                "В перемещении не осталось количества к отправке."
            )
        if (
            not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0)
            or as_of < transfer.updated_at
        ):
            raise StockDocumentTimeError(
                "Нужен явный UTC-момент не раньше текущего состояния перемещения."
            )

    @staticmethod
    def _ensure_warehouses(
        *,
        transfer: StockTransferDispatchDocumentSnapshot,
        transit_id: WarehouseIdVO,
        warehouses: tuple[WarehouseSnapshot, ...],
    ) -> None:
        """Требует ровно три активных склада A/B/T и совпадение T с ранее зафиксированным маршрутом."""
        if not isinstance(transit_id, WarehouseIdVO) or transit_id in (
            transfer.source_warehouse_id,
            transfer.destination_warehouse_id,
        ):
            raise StockTransferTransitMismatchError(
                "Транзитный склад должен отличаться от A и B."
            )
        if transfer.transit is not None and transfer.transit.warehouse_id != transit_id:
            raise StockTransferTransitMismatchError(
                "Транзит уже зафиксирован ранее принятой отправкой."
            )
        if not isinstance(warehouses, tuple):
            raise InvalidWarehouseSnapshotError(
                "Нужен tuple актуальных складов пары отправки."
            )
        ids = set()
        for warehouse in warehouses:
            if not isinstance(warehouse, WarehouseSnapshot):
                raise InvalidWarehouseSnapshotError("Нужны снимки складов A/B/T.")
            StockDocumentConfirmationPolicy.ensure_warehouse(
                warehouse_id=warehouse.id, warehouse=warehouse
            )
            if warehouse.id in ids:
                raise InvalidStockDocumentContextError(
                    "Снимки складов не должны повторяться."
                )
            ids.add(warehouse.id)
        if ids != {
            transfer.source_warehouse_id,
            transfer.destination_warehouse_id,
            transit_id,
        }:
            raise InvalidStockDocumentContextError(
                "Нужны ровно снимки исходного, конечного и транзитного складов."
            )

    @staticmethod
    def _ensure_canonical_reference(reference: str) -> None:
        """Требует канонический UUID в зарезервированном основании, не меняя внешние пользовательские ссылки."""
        try:
            identifier = UUID(reference)
        except (ValueError, TypeError, AttributeError) as exc:
            raise StockDocumentTransferDispatchMismatchError(
                "Основание перемещения должно содержать UUID."
            ) from exc
        if str(identifier) != reference:
            raise StockDocumentTransferDispatchMismatchError(
                "UUID основания должен иметь каноническую строковую форму."
            )
