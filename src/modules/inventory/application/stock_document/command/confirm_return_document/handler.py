from src.modules.inventory.application.stock_document.port.return_origin import (
    ReturnOriginPort,
)
from src.modules.inventory.domain.policy.stock_return import StockReturnPolicy
from src.modules.inventory.application.stock_document.command.confirm_return_document.command import (
    ConfirmReturnDocumentCommand,
)
from src.modules.inventory.application.stock_document.command.confirm_return_document.dto import (
    ConfirmReturnDocumentResultDTO,
    ConfirmReturnDocumentLineDTO,
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
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError


class ConfirmReturnDocumentHandler:
    """Выполняет отдельный сценарий жизненного цикла плана без физического исполнения."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        reader: ReturnDocumentReadService,
        clock: ClockPort,
        items: InventoryItemRepositoryProtocol,
        warehouses: WarehouseRepositoryProtocol,
        origin: ReturnOriginPort,
    ) -> None:
        """Принимает порты общей транзакции; бизнес-решения оставляет агрегату."""
        self._repository, self._reader, self._clock = repository, reader, clock
        self._items = items
        self._warehouses = warehouses
        self._origin = origin

    async def execute(
        self, command: ConfirmReturnDocumentCommand
    ) -> ConfirmReturnDocumentResultDTO:
        """Проверяет версию, вызывает Domain и возвращает сохранённую карточку."""
        document = await self._repository.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ возврата не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_return()
        warehouse = await self._warehouses.get_for_share(document.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        snapshots: dict[UUID, InventoryItemDocumentSnapshot] = {}
        for identifier in sorted(
            {line.inventory_item_id.uuid for line in document.lines}
        ):
            item = await self._items.get_for_update(InventoryItemIdVO(identifier))
            if item is None:
                raise InventoryItemNotFoundError("SKU плановой строки не найден.")
            snapshots[identifier] = item.document_snapshot()
        if document.return_details is None:
            raise StockDocumentNotFoundError("Нет основания возврата.")
        origin = await self._origin.get(
            document.return_details.origin_execution_id, lock=False
        )
        if origin is None:
            raise StockDocumentNotFoundError("Исходное исполнение не найдено.")
        StockReturnPolicy.ensure_plan(
            details=document.return_details,
            warehouse_id=document.warehouse_id,
            owner_id=document.owner_id,
            lines=document.lines,
            origin=origin,
            usage=await self._origin.usage(origin.id),
        )
        document = document.confirm(
            warehouse=warehouse.snapshot(),
            inventory_items=tuple(snapshots.values()),
            updated_at=self._clock.now(),
        )
        await self._repository.save(document, expected_version=command.expected_version)
        result = await self._reader.get(GetReturnDocumentQuery(document.id.uuid))
        return ConfirmReturnDocumentResultDTO(
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
                ConfirmReturnDocumentLineDTO(
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
