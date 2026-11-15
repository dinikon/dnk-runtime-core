from src.modules.inventory.application.stock_execution.query.list_stock_executions.dto import (
    ListStockExecutionsItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as E,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel as T,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel as D,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as W,
)
from src.modules.inventory.infrastructure.accounting.persistence.fact_projection import (
    StockFactProjection,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.dto import (
    GetStockExecutionDetailsResultDTO,
    GetStockExecutionDetailsLineDTO,
    GetStockExecutionDetailsEntryDTO,
    GetStockExecutionDetailsCostDTO,
    GetStockExecutionDetailsAllocationDTO,
)


class StockExecutionQueryMapper:
    """Создаёт собственный контракт факта, отделяя текущие подписи от исторических."""

    @staticmethod
    def details(value: StockFactProjection) -> GetStockExecutionDetailsResultDTO:
        """Берёт количества, связи и стоимость только из нормализованного хранения."""
        execution, posting, document, warehouse = (
            value.execution,
            value.posting,
            value.document,
            value.warehouse,
        )
        historical = (
            {line.id: line for line in value.historical.lines}
            if value.historical
            else {}
        )
        return GetStockExecutionDetailsResultDTO(
            id=execution.id,
            execution_id=execution.id,
            posting_id=posting.id if posting else None,
            document_id=document.id,
            document_version_at_execution=execution.document_version,
            document_current_version=document.version,
            document_current_status=document.status,
            operation_type=execution.operation_type,
            executed_at=execution.executed_at,
            posted_at=posting.posted_at if posting else None,
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=execution.owner_id,
            owner_name=None,
            has_receipt_result=value.historical is not None,
            lines=tuple(
                GetStockExecutionDetailsLineDTO(
                    id=line.id,
                    document_line_id=line.document_line_id,
                    inventory_item_id=line.inventory_item_id,
                    sku=item.sku,
                    sku_at_document=plan.sku,
                    base_uom=line.base_uom,
                    quantity=line.quantity,
                    source_quantity=line.source_quantity,
                    source_uom=line.source_uom,
                    factor_to_base=line.factor_to_base,
                    location_id=line.location_id,
                    location_code=location.code,
                    destination_location_id=line.destination_location_id,
                    destination_location_code=destination.code if destination else None,
                    source_ledger_entry_id=next(
                        (
                            link.ledger_entry_id
                            for link in value.links
                            if link.execution_line_id == line.id
                            and link.role == "SOURCE"
                        ),
                        None,
                    ),
                    destination_ledger_entry_id=next(
                        (
                            link.ledger_entry_id
                            for link in value.links
                            if link.execution_line_id == line.id
                            and link.role == "DESTINATION"
                        ),
                        None,
                    ),
                    lot_id=line.lot_id,
                    lot_number=lot.number if lot else None,
                    serial_id=line.serial_id,
                    serial_number=serial.number if serial else None,
                    stock_status=line.stock_status,
                    ledger_entry_ids=tuple(
                        link.ledger_entry_id
                        for link in value.links
                        if link.execution_line_id == line.id
                    ),
                    sku_at_receipt=(
                        historical[line.id].sku if line.id in historical else None
                    ),
                    serial_number_at_receipt=(
                        historical[line.id].serial_number
                        if line.id in historical
                        else None
                    ),
                    location_code_at_receipt=(
                        historical[line.id].location_code
                        if line.id in historical
                        else None
                    ),
                )
                for line, item, location, lot, serial, plan, destination in value.lines
            ),
            ledger=tuple(
                GetStockExecutionDetailsEntryDTO(
                    entry.id,
                    entry.position_id,
                    entry.quantity_delta,
                    entry.base_uom,
                    tuple(
                        link.execution_line_id
                        for link in value.links
                        if link.ledger_entry_id == entry.id
                    ),
                )
                for entry in value.entries
            ),
            costs=tuple(
                GetStockExecutionDetailsCostDTO(
                    cost.id,
                    cost.total_amount,
                    cost.currency,
                    cost.basis_kind,
                    cost.source_system,
                    cost.source_reference,
                    tuple(
                        GetStockExecutionDetailsAllocationDTO(
                            allocation.execution_line_id, allocation.amount
                        )
                        for allocation in value.allocations
                        if allocation.evidence_id == cost.id
                    ),
                )
                for cost in value.costs
            ),
        )

    @staticmethod
    def to_list_item(
        e: E, t: T | None, d: D, w: W, count: int
    ) -> ListStockExecutionsItemDTO:
        """Преобразует типизированный заголовок и счётчик в DTO собственного списка."""
        return ListStockExecutionsItemDTO(
            e.id,
            d.id,
            d.status,
            e.document_version,
            w.id,
            w.code,
            w.name,
            e.owner_id,
            None,
            e.operation_type,
            e.executed_at,
            t.id if t else None,
            count,
        )
