import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_receipt.dto import (
    PostReceiptLineDTO,
    PostReceiptPositionDTO,
    PostReceiptEntryDTO,
    PostReceiptAllocationDTO,
    PostReceiptCostDTO,
    PostReceiptResultDTO,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution.dto import (
    GetStockExecutionLineDTO,
    GetStockExecutionPositionDTO,
    GetStockExecutionEntryDTO,
    GetStockExecutionAllocationDTO,
    GetStockExecutionCostDTO,
    GetStockExecutionResultDTO,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting.dto import (
    GetStockPostingLineDTO,
    GetStockPostingPositionDTO,
    GetStockPostingEntryDTO,
    GetStockPostingAllocationDTO,
    GetStockPostingCostDTO,
    GetStockPostingResultDTO,
)


class ReceiptPostingRecordMapper:
    """Преобразует только доверенный JSONB снимок конкретной завершённой команды."""

    @staticmethod
    def to_record(result: PostReceiptResultDTO) -> dict[str, Any]:
        """Сохраняет Decimal строками без потери исходной точности."""
        return json.loads(json.dumps(asdict(result), default=str))

    @staticmethod
    def to_command(record: dict[str, Any]) -> PostReceiptResultDTO:
        """Возвращает собственный DTO сценария из неизменяемого снимка."""
        return PostReceiptResultDTO(
            document_id=UUID(record["document_id"]),
            document_version_before=record["document_version_before"],
            document_version_after=record["document_version_after"],
            document_status=record["document_status"],
            execution_id=UUID(record["execution_id"]),
            posting_id=UUID(record["posting_id"]),
            event_id=UUID(record["event_id"]),
            actor_id=UUID(record["actor_id"]),
            warehouse_id=UUID(record["warehouse_id"]),
            warehouse_code=record["warehouse_code"],
            warehouse_name=record["warehouse_name"],
            owner_id=UUID(record["owner_id"]),
            owner_name=record["owner_name"],
            posted_at=datetime.fromisoformat(record["posted_at"]),
            lines=tuple(
                PostReceiptLineDTO(
                    id=UUID(row["id"]),
                    client_line_id=UUID(row["client_line_id"]),
                    document_line_id=UUID(row["document_line_id"]),
                    inventory_item_id=UUID(row["inventory_item_id"]),
                    sku=row["sku"],
                    base_uom=row["base_uom"],
                    quantity=Decimal(row["quantity"]),
                    source_quantity=Decimal(row["source_quantity"]),
                    source_uom=row["source_uom"],
                    factor_to_base=Decimal(row["factor_to_base"]),
                    location_id=UUID(row["location_id"]),
                    location_code=row["location_code"],
                    lot_id=UUID(row["lot_id"]) if row["lot_id"] is not None else None,
                    lot_number=row["lot_number"],
                    serial_id=(
                        UUID(row["serial_id"]) if row["serial_id"] is not None else None
                    ),
                    serial_number=row["serial_number"],
                    stock_status=row["stock_status"],
                    position_id=UUID(row["position_id"]),
                    ledger_entry_id=UUID(row["ledger_entry_id"]),
                )
                for row in record["lines"]
            ),
            positions=tuple(
                PostReceiptPositionDTO(
                    id=UUID(row["id"]),
                    base_uom=row["base_uom"],
                    before_quantity=Decimal(row["before_quantity"]),
                    delta=Decimal(row["delta"]),
                    after_quantity=Decimal(row["after_quantity"]),
                    before_version=row["before_version"],
                    after_version=row["after_version"],
                )
                for row in record["positions"]
            ),
            ledger=tuple(
                PostReceiptEntryDTO(
                    id=UUID(row["id"]),
                    position_id=UUID(row["position_id"]),
                    quantity_delta=Decimal(row["quantity_delta"]),
                    base_uom=row["base_uom"],
                )
                for row in record["ledger"]
            ),
            costs=tuple(
                PostReceiptCostDTO(
                    id=UUID(row["id"]),
                    amount=Decimal(row["amount"]),
                    currency=row["currency"],
                    basis_kind=row["basis_kind"],
                    source_system=row["source_system"],
                    source_reference=row["source_reference"],
                    allocations=tuple(
                        PostReceiptAllocationDTO(
                            UUID(a["execution_line_id"]), Decimal(a["amount"])
                        )
                        for a in row["allocations"]
                    ),
                )
                for row in record["costs"]
            ),
        )

    @staticmethod
    def to_execution(record: dict[str, Any]) -> GetStockExecutionResultDTO:
        """Возвращает собственный DTO сценария из неизменяемого снимка."""
        return GetStockExecutionResultDTO(
            document_id=UUID(record["document_id"]),
            document_version_before=record["document_version_before"],
            document_version_after=record["document_version_after"],
            document_status=record["document_status"],
            execution_id=UUID(record["execution_id"]),
            posting_id=UUID(record["posting_id"]),
            event_id=UUID(record["event_id"]),
            actor_id=UUID(record["actor_id"]),
            warehouse_id=UUID(record["warehouse_id"]),
            warehouse_code=record["warehouse_code"],
            warehouse_name=record["warehouse_name"],
            owner_id=UUID(record["owner_id"]),
            owner_name=record["owner_name"],
            posted_at=datetime.fromisoformat(record["posted_at"]),
            lines=tuple(
                GetStockExecutionLineDTO(
                    id=UUID(row["id"]),
                    client_line_id=UUID(row["client_line_id"]),
                    document_line_id=UUID(row["document_line_id"]),
                    inventory_item_id=UUID(row["inventory_item_id"]),
                    sku=row["sku"],
                    base_uom=row["base_uom"],
                    quantity=Decimal(row["quantity"]),
                    source_quantity=Decimal(row["source_quantity"]),
                    source_uom=row["source_uom"],
                    factor_to_base=Decimal(row["factor_to_base"]),
                    location_id=UUID(row["location_id"]),
                    location_code=row["location_code"],
                    lot_id=UUID(row["lot_id"]) if row["lot_id"] is not None else None,
                    lot_number=row["lot_number"],
                    serial_id=(
                        UUID(row["serial_id"]) if row["serial_id"] is not None else None
                    ),
                    serial_number=row["serial_number"],
                    stock_status=row["stock_status"],
                    position_id=UUID(row["position_id"]),
                    ledger_entry_id=UUID(row["ledger_entry_id"]),
                )
                for row in record["lines"]
            ),
            positions=tuple(
                GetStockExecutionPositionDTO(
                    id=UUID(row["id"]),
                    base_uom=row["base_uom"],
                    before_quantity=Decimal(row["before_quantity"]),
                    delta=Decimal(row["delta"]),
                    after_quantity=Decimal(row["after_quantity"]),
                    before_version=row["before_version"],
                    after_version=row["after_version"],
                )
                for row in record["positions"]
            ),
            ledger=tuple(
                GetStockExecutionEntryDTO(
                    id=UUID(row["id"]),
                    position_id=UUID(row["position_id"]),
                    quantity_delta=Decimal(row["quantity_delta"]),
                    base_uom=row["base_uom"],
                )
                for row in record["ledger"]
            ),
            costs=tuple(
                GetStockExecutionCostDTO(
                    id=UUID(row["id"]),
                    amount=Decimal(row["amount"]),
                    currency=row["currency"],
                    basis_kind=row["basis_kind"],
                    source_system=row["source_system"],
                    source_reference=row["source_reference"],
                    allocations=tuple(
                        GetStockExecutionAllocationDTO(
                            UUID(a["execution_line_id"]), Decimal(a["amount"])
                        )
                        for a in row["allocations"]
                    ),
                )
                for row in record["costs"]
            ),
        )

    @staticmethod
    def to_posting(record: dict[str, Any]) -> GetStockPostingResultDTO:
        """Возвращает собственный DTO сценария из неизменяемого снимка."""
        return GetStockPostingResultDTO(
            document_id=UUID(record["document_id"]),
            document_version_before=record["document_version_before"],
            document_version_after=record["document_version_after"],
            document_status=record["document_status"],
            execution_id=UUID(record["execution_id"]),
            posting_id=UUID(record["posting_id"]),
            event_id=UUID(record["event_id"]),
            actor_id=UUID(record["actor_id"]),
            warehouse_id=UUID(record["warehouse_id"]),
            warehouse_code=record["warehouse_code"],
            warehouse_name=record["warehouse_name"],
            owner_id=UUID(record["owner_id"]),
            owner_name=record["owner_name"],
            posted_at=datetime.fromisoformat(record["posted_at"]),
            lines=tuple(
                GetStockPostingLineDTO(
                    id=UUID(row["id"]),
                    client_line_id=UUID(row["client_line_id"]),
                    document_line_id=UUID(row["document_line_id"]),
                    inventory_item_id=UUID(row["inventory_item_id"]),
                    sku=row["sku"],
                    base_uom=row["base_uom"],
                    quantity=Decimal(row["quantity"]),
                    source_quantity=Decimal(row["source_quantity"]),
                    source_uom=row["source_uom"],
                    factor_to_base=Decimal(row["factor_to_base"]),
                    location_id=UUID(row["location_id"]),
                    location_code=row["location_code"],
                    lot_id=UUID(row["lot_id"]) if row["lot_id"] is not None else None,
                    lot_number=row["lot_number"],
                    serial_id=(
                        UUID(row["serial_id"]) if row["serial_id"] is not None else None
                    ),
                    serial_number=row["serial_number"],
                    stock_status=row["stock_status"],
                    position_id=UUID(row["position_id"]),
                    ledger_entry_id=UUID(row["ledger_entry_id"]),
                )
                for row in record["lines"]
            ),
            positions=tuple(
                GetStockPostingPositionDTO(
                    id=UUID(row["id"]),
                    base_uom=row["base_uom"],
                    before_quantity=Decimal(row["before_quantity"]),
                    delta=Decimal(row["delta"]),
                    after_quantity=Decimal(row["after_quantity"]),
                    before_version=row["before_version"],
                    after_version=row["after_version"],
                )
                for row in record["positions"]
            ),
            ledger=tuple(
                GetStockPostingEntryDTO(
                    id=UUID(row["id"]),
                    position_id=UUID(row["position_id"]),
                    quantity_delta=Decimal(row["quantity_delta"]),
                    base_uom=row["base_uom"],
                )
                for row in record["ledger"]
            ),
            costs=tuple(
                GetStockPostingCostDTO(
                    id=UUID(row["id"]),
                    amount=Decimal(row["amount"]),
                    currency=row["currency"],
                    basis_kind=row["basis_kind"],
                    source_system=row["source_system"],
                    source_reference=row["source_reference"],
                    allocations=tuple(
                        GetStockPostingAllocationDTO(
                            UUID(a["execution_line_id"]), Decimal(a["amount"])
                        )
                        for a in row["allocations"]
                    ),
                )
                for row in record["costs"]
            ),
        )
