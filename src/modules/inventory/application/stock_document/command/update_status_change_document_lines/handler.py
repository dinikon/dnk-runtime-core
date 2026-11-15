from src.modules.inventory.domain.stock_document.value_object.status_change_details import (
    StockStatusChangeDetailsVO,
)
from src.modules.inventory.domain.stock_document.value_object.status_change_reason import (
    StatusChangeReasonVO,
)
from src.modules.inventory.application.stock_document.command.update_status_change_document_lines.command import (
    UpdateStatusChangeDocumentLinesCommand,
)
from src.modules.inventory.application.stock_document.command.update_status_change_document_lines.dto import (
    UpdateStatusChangeDocumentLinesResultDTO,
    UpdateStatusChangeDocumentLinesLineDTO,
)
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.status_change_read_service import (
    StatusChangeDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.query import (
    GetStatusChangeDocumentQuery,
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
from src.modules.inventory.application.stock_document.command.update_status_change_document_lines.command import (
    ExistingStatusChangeLine,
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


class UpdateStatusChangeDocumentLinesHandler:
    """Выполняет отдельный сценарий жизненного цикла плана без физического исполнения."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        reader: StatusChangeDocumentReadService,
        clock: ClockPort,
        items: InventoryItemRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общей транзакции; бизнес-решения оставляет агрегату."""
        self._repository, self._reader, self._clock = repository, reader, clock
        self._items = items
        self._uuid = uuid

    async def execute(
        self, command: UpdateStatusChangeDocumentLinesCommand
    ) -> UpdateStatusChangeDocumentLinesResultDTO:
        """Проверяет версию, вызывает Domain и возвращает сохранённую карточку."""
        document = await self._repository.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ изменения состояния не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_status_change()
        document.ensure_can_edit_lines()
        now = self._clock.now()
        if command.reason is not None or command.target_status is not None:
            current = document.status_change_snapshot()
            document = document.change_status_change_details(
                StockStatusChangeDetailsVO(
                    (
                        command.target_status
                        if command.target_status is not None
                        else current.target_status
                    ),
                    (
                        StatusChangeReasonVO(command.reason)
                        if command.reason is not None
                        else current.reason
                    ),
                ),
                updated_at=now,
            )
        if command.lines is not None:
            existing_ids = {
                value.id
                for value in command.lines
                if isinstance(value, ExistingStatusChangeLine)
            }
            identifiers = set()
            for value in command.lines:
                if isinstance(value, ExistingStatusChangeLine):
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
                if not isinstance(value, ExistingStatusChangeLine):
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
                if isinstance(value, ExistingStatusChangeLine):
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
        result = await self._reader.get(GetStatusChangeDocumentQuery(document.id.uuid))
        return UpdateStatusChangeDocumentLinesResultDTO(
            id=result.id,
            operation_type=result.operation_type,
            status=result.status,
            warehouse_id=result.warehouse_id,
            warehouse_code=result.warehouse_code,
            warehouse_name=result.warehouse_name,
            owner_id=result.owner_id,
            owner_name=result.owner_name,
            reason=result.reason,
            target_status=result.target_status,
            source_system=result.source_system,
            source_reference=result.source_reference,
            source_version=result.source_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            version=result.version,
            lines=tuple(
                UpdateStatusChangeDocumentLinesLineDTO(
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
