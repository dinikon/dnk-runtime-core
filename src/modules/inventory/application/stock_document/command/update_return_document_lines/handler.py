from src.modules.inventory.application.stock_document.port.return_origin import (
    ReturnOriginPort,
)
from src.modules.inventory.domain.policy.stock_return import StockReturnPolicy
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_reason import (
    ReturnReasonVO,
)
from src.modules.inventory.application.stock_document.command.update_return_document_lines.command import (
    UpdateReturnDocumentLinesCommand,
)
from src.modules.inventory.application.stock_document.command.update_return_document_lines.dto import (
    UpdateReturnDocumentLinesResultDTO,
    UpdateReturnDocumentLinesLineDTO,
)
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.return_read_service import (
    ReturnDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
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
from src.modules.inventory.application.stock_document.command.update_return_document_lines.command import (
    ExistingReturnLine,
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


class UpdateReturnDocumentLinesHandler:
    """Выполняет отдельный сценарий жизненного цикла плана без физического исполнения."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        reader: ReturnDocumentReadService,
        clock: ClockPort,
        items: InventoryItemRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
        origin: ReturnOriginPort,
    ) -> None:
        """Принимает порты общей транзакции; бизнес-решения оставляет агрегату."""
        self._repository, self._reader, self._clock = repository, reader, clock
        self._items = items
        self._uuid = uuid
        self._origin = origin

    async def execute(
        self, command: UpdateReturnDocumentLinesCommand
    ) -> UpdateReturnDocumentLinesResultDTO:
        """Проверяет версию, вызывает Domain и возвращает сохранённую карточку."""
        document = await self._repository.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ возврата не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_return()
        document.ensure_can_edit_lines()
        now = self._clock.now()
        if document.return_details is None:
            raise StockDocumentNotFoundError("Нет основания возврата.")
        origin = await self._origin.get(
            document.return_details.origin_execution_id, lock=False
        )
        if origin is None:
            raise StockDocumentNotFoundError("Исходное исполнение не найдено.")
        if command.reason is not None:
            document = document.change_return_reason(
                ReturnReasonVO(command.reason), updated_at=now
            )
        if command.lines is not None:
            existing_ids = {
                value.id
                for value in command.lines
                if isinstance(value, ExistingReturnLine)
            }
            identifiers = set()
            for value in command.lines:
                if isinstance(value, ExistingReturnLine):
                    identifiers.add(
                        document.get_line(
                            StockDocumentLineIdVO(value.id)
                        ).inventory_item_id.uuid
                    )
                else:
                    identifiers.add(
                        StockReturnPolicy.line(
                            origin,
                            StockExecutionLineIdVO(value.origin_execution_line_id),
                        ).dimensions.inventory_item_id.uuid
                    )
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
                if not isinstance(value, ExistingReturnLine):
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
                if isinstance(value, ExistingReturnLine):
                    continue
                try:
                    source = StockReturnPolicy.line(
                        origin, StockExecutionLineIdVO(value.origin_execution_line_id)
                    )
                    snapshot = snapshots[source.dimensions.inventory_item_id.uuid]
                    line = StockDocumentLine.create(
                        identifier=StockDocumentLineIdVO(self._uuid.new()),
                        inventory_item=snapshot,
                        return_origin_line_id=source.id,
                        quantity=QuantityVO(value.quantity),
                        uom=UomCodeVO(value.uom),
                    )
                    document = document.add_line(
                        line, inventory_item=snapshot, updated_at=now
                    )
                except DomainError as exc:
                    raise StockDocumentLineCreationError(position, str(exc)) from exc
        StockReturnPolicy.ensure_plan(
            details=document.return_snapshot(),
            warehouse_id=document.warehouse_id,
            owner_id=document.owner_id,
            lines=document.lines,
            origin=origin,
            usage=await self._origin.usage(origin.id),
        )
        await self._repository.save(document, expected_version=command.expected_version)
        result = await self._reader.get(GetReturnDocumentQuery(document.id.uuid))
        return UpdateReturnDocumentLinesResultDTO(
            id=result.id,
            operation_type=result.operation_type,
            status=result.status,
            warehouse_id=result.warehouse_id,
            warehouse_code=result.warehouse_code,
            warehouse_name=result.warehouse_name,
            owner_id=result.owner_id,
            owner_name=result.owner_name,
            reason=result.reason,
            direction=result.direction,
            origin_execution_id=result.origin_execution_id,
            source_system=result.source_system,
            source_reference=result.source_reference,
            source_version=result.source_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            version=result.version,
            lines=tuple(
                UpdateReturnDocumentLinesLineDTO(
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
                    origin_execution_line_id=line.origin_execution_line_id,
                )
                for line in result.lines
            ),
        )
