from src.modules.inventory.domain.stock_execution.value_object.return_receipt_route import (
    ReturnReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.return_issue_route import (
    ReturnIssueExecutionRouteVO,
)
from uuid import UUID
from src.modules.inventory.domain.stock_document.return_posting import (
    ReturnPostingResult,
)
from src.modules.inventory.application.stock_document.command.post_return.command import (
    PostReturnCommand,
)
from src.modules.inventory.application.stock_document.query.get_return_document.dto import (
    GetReturnDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.command.post_return.dto import (
    PostReturnLineDTO,
    PostReturnPositionDTO,
    PostReturnEntryDTO,
    PostReturnResultDTO,
)


def return_result(
    *,
    command: PostReturnCommand,
    bundle: ReturnPostingResult,
    header: GetReturnDocumentResultDTO,
    location_codes: dict[UUID, str],
    lot_numbers: dict[UUID, str],
    serial_numbers: dict[UUID, str],
) -> PostReturnResultDTO:
    """Фиксирует исходный результат операции, отличая остаток после неё от будущего текущего остатка."""
    if bundle.execution.return_details is None:
        raise RuntimeError("Сохранённое возврат не содержит причины.")
    after = {position.id: position for position in bundle.after}
    position_by_dims = {position.dimensions: position for position in bundle.before}
    entries = {entry.position_id: entry for entry in bundle.posting.entries}
    doc_lines = {line.id: line for line in bundle.document.lines}
    rows = []
    for value, line in zip(command.lines, bundle.execution.lines, strict=True):
        if not isinstance(
            line.route, (ReturnReceiptExecutionRouteVO, ReturnIssueExecutionRouteVO)
        ):
            raise RuntimeError("Неверный сохранённый маршрут возврата.")
        dims = line.route.dimensions[0]
        position = position_by_dims[dims]
        rows.append(
            PostReturnLineDTO(
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
                line.route.origin_line_id.uuid,
            )
        )
    return PostReturnResultDTO(
        document_id=bundle.document.id.uuid,
        document_version_before=command.expected_version,
        document_version_after=bundle.document.version,
        document_status=bundle.document.status.value,
        execution_id=bundle.execution.id.uuid,
        posting_id=bundle.posting.id.uuid,
        event_id=bundle.event.event_id.uuid,
        actor_id=command.actor_id,
        warehouse_id=bundle.document.warehouse_id.uuid,
        warehouse_code=header.warehouse_code,
        warehouse_name=header.warehouse_name,
        owner_id=bundle.document.owner_id.uuid,
        owner_name=header.owner_name,
        reason=bundle.execution.return_details.reason.value,
        direction=bundle.execution.return_details.direction.value,
        origin_execution_id=bundle.execution.return_details.origin_execution_id.uuid,
        posted_at=bundle.posting.posted_at,
        lines=tuple(rows),
        positions=tuple(
            PostReturnPositionDTO(
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
            PostReturnEntryDTO(
                e.id.uuid, e.position_id.uuid, e.quantity_delta.value, e.base_uom.value
            )
            for e in bundle.posting.entries
        ),
    )
