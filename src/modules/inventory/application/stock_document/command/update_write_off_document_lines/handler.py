from src.modules.inventory.domain.stock_document.value_object.write_off_reason import (
    WriteOffReasonVO,
)
from src.modules.inventory.application.stock_document.command.update_write_off_document_lines.command import (
    UpdateWriteOffDocumentLinesCommand,
)
from src.modules.inventory.application.stock_document.command.update_write_off_document_lines.dto import (
    UpdateWriteOffDocumentLinesResultDTO,
    UpdateWriteOffDocumentLinesLineDTO,
)
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.write_off_read_service import (
    WriteOffDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
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
from src.modules.inventory.application.stock_document.command.update_write_off_document_lines.command import (
    ExistingWriteOffLine,
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


class UpdateWriteOffDocumentLinesHandler:
    """Выполняет отдельный сценарий жизненного цикла плана без физического исполнения."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        reader: WriteOffDocumentReadService,
        clock: ClockPort,
        items: InventoryItemRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общей транзакции; бизнес-решения оставляет агрегату."""
        self._repository, self._reader, self._clock = repository, reader, clock
        self._items = items
        self._uuid = uuid

    async def execute(
        self, command: UpdateWriteOffDocumentLinesCommand
    ) -> UpdateWriteOffDocumentLinesResultDTO:
        """Проверяет версию, вызывает Domain и возвращает сохранённую карточку."""
        document = await self._repository.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ списания не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_write_off()
        document.ensure_can_edit_lines()
        now = self._clock.now()
        if command.reason is not None:
            document = document.change_write_off_reason(
                WriteOffReasonVO(command.reason), updated_at=now
            )
        if command.lines is not None:
            existing_ids = {
                value.id
                for value in command.lines
                if isinstance(value, ExistingWriteOffLine)
            }
            identifiers = set()
            for value in command.lines:
                if isinstance(value, ExistingWriteOffLine):
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
            for line in document.lines:
                if line.id.uuid not in existing_ids:
                    document = document.remove_line(line.id, updated_at=now)
            # Существующие строки меняются на прежних местах, новые добавляются в конце.
            for position, value in enumerate(command.lines):
                if not isinstance(value, ExistingWriteOffLine):
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
                if isinstance(value, ExistingWriteOffLine):
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
        result = await self._reader.get(GetWriteOffDocumentQuery(document.id.uuid))
        return UpdateWriteOffDocumentLinesResultDTO(
            id=result.id,
            operation_type=result.operation_type,
            status=result.status,
            warehouse_id=result.warehouse_id,
            warehouse_code=result.warehouse_code,
            warehouse_name=result.warehouse_name,
            owner_id=result.owner_id,
            owner_name=result.owner_name,
            reason=result.reason,
            source_system=result.source_system,
            source_reference=result.source_reference,
            source_version=result.source_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            version=result.version,
            lines=tuple(
                UpdateWriteOffDocumentLinesLineDTO(
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
                    remaining_qty=line.remaining_qty,
                )
                for line in result.lines
            ),
        )
