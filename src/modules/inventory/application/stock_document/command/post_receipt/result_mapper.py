from uuid import UUID
from src.modules.inventory.domain.stock_document.receipt_posting import (
    ReceiptPostingResult,
)
from src.modules.inventory.application.stock_document.command.post_receipt.command import (
    PostReceiptCommand,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.dto import (
    GetReceiptDocumentResultDTO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.application.stock_document.command.post_receipt.dto import (
    PostReceiptLineDTO,
    PostReceiptPositionDTO,
    PostReceiptEntryDTO,
    PostReceiptAllocationDTO,
    PostReceiptCostDTO,
    PostReceiptResultDTO,
)


def receipt_result(
    *,
    command: PostReceiptCommand,
    bundle: ReceiptPostingResult,
    header: GetReceiptDocumentResultDTO,
    location_codes: dict[UUID, str],
    lot_numbers: dict[UUID, str],
    serial_numbers: dict[UUID, str],
) -> PostReceiptResultDTO:
    """Фиксирует исходный результат операции, отличая остаток после неё от будущего текущего остатка."""
    before = {position.id: position for position in bundle.before}
    after = {position.id: position for position in bundle.after}
    position_by_dims = {position.dimensions: position for position in bundle.before}
    entries = {entry.position_id: entry for entry in bundle.posting.entries}
    doc_lines = {line.id: line for line in bundle.document.lines}
    rows = []
    for value, line in zip(command.lines, bundle.execution.lines, strict=True):
        dims = line.route.dimensions[0]
        position = position_by_dims[dims]
        rows.append(
            PostReceiptLineDTO(
                line.id.uuid,
                value.client_line_id,
                line.document_line_id.uuid,
                line.inventory_item_id.uuid,
                doc_lines[line.document_line_id].sku.value,
                line.base_uom.value,
                line.quantity.value,
                line.conversion.quantity.value,
                line.conversion.uom.value,
                line.conversion.factor_to_base,
                dims.location_id.uuid,
                location_codes[dims.location_id.uuid],
                dims.lot_id.uuid if dims.lot_id else None,
                lot_numbers.get(dims.lot_id.uuid) if dims.lot_id else None,
                dims.serial_id.uuid if dims.serial_id else None,
                serial_numbers.get(dims.serial_id.uuid) if dims.serial_id else None,
                dims.stock_status.value,
                position.id.uuid,
                entries[position.id].id.uuid,
            )
        )
    return PostReceiptResultDTO(
        document_id=bundle.document.id.uuid,
        document_version_before=command.expected_version,
        document_version_after=bundle.document.version,
        document_status=bundle.document.status.value,
        execution_id=bundle.execution.id.uuid,
        posting_id=bundle.posting.id.uuid,
        event_id=bundle.event.event_id,
        actor_id=command.actor_id,
        warehouse_id=bundle.document.warehouse_id.uuid,
        warehouse_code=header.warehouse_code,
        warehouse_name=header.warehouse_name,
        owner_id=bundle.document.owner_id.uuid,
        owner_name=header.owner_name,
        posted_at=bundle.posting.posted_at,
        lines=tuple(rows),
        positions=tuple(
            PostReceiptPositionDTO(
                value.id.uuid,
                value.base_uom.value,
                value.on_hand_qty.value,
                entries[value.id].quantity_delta.value,
                after[value.id].on_hand_qty.value,
                value.version,
                after[value.id].version,
            )
            for value in bundle.before
        ),
        ledger=tuple(
            PostReceiptEntryDTO(
                e.id.uuid, e.position_id.uuid, e.quantity_delta.value, e.base_uom.value
            )
            for e in bundle.posting.entries
        ),
        costs=tuple(
            PostReceiptCostDTO(
                c.id,
                c.total.amount,
                c.total.currency.value,
                c.basis_kind,
                c.source_system,
                c.source_reference,
                tuple(
                    PostReceiptAllocationDTO(a.execution_line_id.uuid, a.amount.amount)
                    for a in c.allocations
                ),
            )
            for c in bundle.execution.receipt_cost_evidence
        ),
    )
