from src.modules.inventory.application.stock_document.status_change_context import (
    StatusChangeContextLoader,
    StatusChangeFacts,
    StatusChangeFactLine,
    calculate_status_change,
)
from src.modules.inventory.application.stock_document.query.preview_status_change.query import (
    PreviewStatusChangeQuery,
)
from src.modules.inventory.application.stock_document.query.preview_status_change.dto import (
    PreviewStatusChangeResultDTO,
    StatusChangePreviewPositionDTO,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class PreviewStatusChangeHandler:
    """Считает предварительный результат через общий Domain без записывающих портов."""

    def __init__(
        self,
        loader: StatusChangeContextLoader,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает подготовку только для чтения, часы и временные идентичности расчёта."""
        self._loader, self._clock, self._uuid = loader, clock, uuid

    async def execute(
        self, query: PreviewStatusChangeQuery
    ) -> PreviewStatusChangeResultDTO:
        """Проверяет те же правила, что проведение, и возвращает только предварительные количества."""
        context = await self._loader.load(
            StatusChangeFacts(
                query.document_id,
                query.expected_version,
                tuple(
                    StatusChangeFactLine(
                        v.client_line_id,
                        v.document_line_id,
                        v.source_position_id,
                        v.quantity,
                        v.uom,
                    )
                    for v in query.lines
                ),
            ),
            lock=False,
        )
        bundle = calculate_status_change(
            context, now=self._clock.now(), uuid=self._uuid
        )
        details = context.document.status_change_snapshot()
        items = {
            line.inventory_item_id: line.sku.value for line in context.document.lines
        }
        after = {position.id: position for position in bundle.after}
        entries = {entry.position_id: entry for entry in bundle.posting.entries}
        rows = []
        for position in bundle.before:
            d = position.dimensions
            entry = entries[position.id]
            rows.append(
                StatusChangePreviewPositionDTO(
                    (
                        None
                        if position.id in context.new_position_ids
                        else position.id.uuid
                    ),
                    position.id not in context.new_position_ids,
                    "SOURCE" if entry.quantity_delta.value < 0 else "DESTINATION",
                    d.inventory_item_id.uuid,
                    items[d.inventory_item_id],
                    d.location_id.uuid,
                    context.location_codes[d.location_id.uuid],
                    d.stock_status.value,
                    d.lot_id.uuid if d.lot_id else None,
                    context.lot_numbers.get(d.lot_id.uuid) if d.lot_id else None,
                    d.serial_id.uuid if d.serial_id else None,
                    (
                        context.serial_numbers.get(d.serial_id.uuid)
                        if d.serial_id
                        else None
                    ),
                    position.base_uom.value,
                    position.on_hand_qty.value,
                    entry.quantity_delta.value,
                    after[position.id].on_hand_qty.value,
                )
            )
        return PreviewStatusChangeResultDTO(
            context.document.id.uuid,
            context.document.version,
            details.reason.value,
            details.target_status.value,
            tuple(rows),
        )
