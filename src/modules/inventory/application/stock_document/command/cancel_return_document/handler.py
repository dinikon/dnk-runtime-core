from src.modules.inventory.application.stock_document.command.cancel_return_document.command import (
    CancelReturnDocumentCommand,
)
from src.modules.inventory.application.stock_document.command.cancel_return_document.dto import (
    CancelReturnDocumentResultDTO,
    CancelReturnDocumentLineDTO,
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


class CancelReturnDocumentHandler:
    """Выполняет отдельный сценарий жизненного цикла плана без физического исполнения."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        reader: ReturnDocumentReadService,
        clock: ClockPort,
    ) -> None:
        """Принимает порты общей транзакции; бизнес-решения оставляет агрегату."""
        self._repository, self._reader, self._clock = repository, reader, clock

    async def execute(
        self, command: CancelReturnDocumentCommand
    ) -> CancelReturnDocumentResultDTO:
        """Проверяет версию, вызывает Domain и возвращает сохранённую карточку."""
        document = await self._repository.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ возврата не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_return()
        document = document.cancel(updated_at=self._clock.now())
        await self._repository.save(document, expected_version=command.expected_version)
        result = await self._reader.get(GetReturnDocumentQuery(document.id.uuid))
        return CancelReturnDocumentResultDTO(
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
                CancelReturnDocumentLineDTO(
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
