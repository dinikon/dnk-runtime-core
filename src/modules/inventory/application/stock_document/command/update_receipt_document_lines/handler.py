from src.modules.inventory.application.stock_document.command.update_receipt_document_lines.command import (
    UpdateReceiptDocumentLinesCommand,
)
from src.modules.inventory.application.stock_document.command.update_receipt_document_lines.dto import (
    UpdateReceiptDocumentLinesResultDTO,
    UpdateReceiptDocumentLinesLineDTO,
)
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.read_service import (
    ReceiptDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.query import (
    GetReceiptDocumentQuery,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from uuid import UUID
from src.modules.inventory.application.stock_document.command.update_receipt_document_lines.command import (
    ExistingReceiptLine,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineCreationError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class UpdateReceiptDocumentLinesHandler:
    """Выполняет отдельный сценарий жизненного цикла плана без физического исполнения."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        reader: ReceiptDocumentReadService,
        clock: ClockPort,
        items: InventoryItemRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общей транзакции; бизнес-решения оставляет агрегату."""
        self._repository, self._reader, self._clock = repository, reader, clock
        self._items = items
        self._uuid = uuid

    async def execute(
        self, command: UpdateReceiptDocumentLinesCommand
    ) -> UpdateReceiptDocumentLinesResultDTO:
        """Проверяет версию, вызывает Domain и возвращает сохранённую карточку."""
        document = await self._repository.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ поступления не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_receipt()
        document.ensure_can_edit_lines()
        existing_ids = {
            value.id
            for value in command.lines
            if isinstance(value, ExistingReceiptLine)
        }
        identifiers = set()
        for value in command.lines:
            if isinstance(value, ExistingReceiptLine):
                identifiers.add(
                    document.get_line(
                        StockDocumentLineIdVO(value.id)
                    ).inventory_item_id.uuid
                )
            else:
                identifiers.add(value.inventory_item_id)
        snapshots: dict[UUID, InventoryItemDocumentSnapshot] = {}
        for identifier in sorted(identifiers):
            item = await self._items.get_for_update(InventoryItemIdVO(identifier))
            if item is None:
                raise InventoryItemNotFoundError("SKU плановой строки не найден.")
            snapshots[identifier] = item.document_snapshot()
        now = self._clock.now()
        for line in document.lines:
            if line.id.uuid not in existing_ids:
                document = document.remove_line(line.id, updated_at=now)
        # Существующие строки меняются на прежних местах, новые добавляются в конце.
        for position, value in enumerate(command.lines):
            if not isinstance(value, ExistingReceiptLine):
                continue
            try:
                line = document.get_line(StockDocumentLineIdVO(value.id))
                document = document.change_line(
                    identifier=line.id,
                    quantity=QuantityVO(value.quantity),
                    uom=UomCodeVO(value.uom),
                    inventory_item=snapshots[line.inventory_item_id.uuid],
                    updated_at=now,
                )
            except DomainError as exc:
                raise StockDocumentLineCreationError(position, str(exc)) from exc
        for position, value in enumerate(command.lines):
            if isinstance(value, ExistingReceiptLine):
                continue
            try:
                snapshot = snapshots[value.inventory_item_id]
                line = StockDocumentLine.create(
                    identifier=StockDocumentLineIdVO(self._uuid.new()),
                    inventory_item=snapshot,
                    quantity=QuantityVO(value.quantity),
                    uom=UomCodeVO(value.uom),
                )
                document = document.add_line(
                    line, inventory_item=snapshot, updated_at=now
                )
            except DomainError as exc:
                raise StockDocumentLineCreationError(position, str(exc)) from exc
        await self._repository.save(document, expected_version=command.expected_version)
        result = await self._reader.get(GetReceiptDocumentQuery(document.id.uuid))
        return UpdateReceiptDocumentLinesResultDTO(
            id=result.id,
            operation_type=result.operation_type,
            status=result.status,
            warehouse_id=result.warehouse_id,
            warehouse_code=result.warehouse_code,
            warehouse_name=result.warehouse_name,
            owner_id=result.owner_id,
            owner_name=result.owner_name,
            source_system=result.source_system,
            source_reference=result.source_reference,
            source_version=result.source_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            version=result.version,
            lines=tuple(
                UpdateReceiptDocumentLinesLineDTO(
                    id=line.id,
                    position=line.position,
                    inventory_item_id=line.inventory_item_id,
                    sku=line.sku,
                    base_uom=line.base_uom,
                    planned_qty=line.planned_qty,
                    source_quantity=line.source_quantity,
                    source_uom=line.source_uom,
                    factor_to_base=line.factor_to_base,
                    executed_qty=line.executed_qty,
                )
                for line in result.lines
            ),
        )
