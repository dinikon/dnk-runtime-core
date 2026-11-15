from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.receipt_cost import (
    ReceiptCostEvidence,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.inventory_item.execution_snapshot import (
    InventoryItemExecutionSnapshot,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.policy.receipt_serial_presence import (
    ReceiptSerialPresencePolicy,
)


@dataclass(frozen=True, slots=True)
class StockReceiptPosted:
    """Доменный факт согласованного изменения документа, позиций и физического журнала."""

    event_id: UUID
    execution_id: UUID
    posting_id: UUID
    document_id: UUID
    document_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ReceiptPostingResult:
    """Передаёт чистый согласованный результат нескольких агрегатов, не владея их жизненными циклами."""

    document: StockDocument
    execution: StockExecution
    posting: StockPosting
    before: tuple[StockPosition, ...]
    after: tuple[StockPosition, ...]
    event: StockReceiptPosted


class ReceiptPostingService:
    """Строит полный результат приёмки без SQL, репозиториев и управления транзакцией."""

    @staticmethod
    def post(
        *,
        document: StockDocument,
        expected_version: int,
        execution_id: StockExecutionIdVO,
        posting_id: StockPostingIdVO,
        event_id: UUID,
        lines: tuple[StockExecutionLine, ...],
        positions: tuple[StockPosition, ...],
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemExecutionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...],
        serials: tuple[StockSerialSnapshot, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
        costs: tuple[ReceiptCostEvidence, ...],
        now: datetime,
    ) -> ReceiptPostingResult:
        """Проверяет факт и присутствие, строит Ledger, применяет каждую запись один раз и регистрирует прогресс."""
        document.ensure_version(expected_version)
        document.ensure_manual_receipt()
        execution = StockExecution.create(
            identifier=execution_id,
            document=document.execution_snapshot(),
            executed_at=now,
            lines=lines,
            warehouse=warehouse,
            inventory_items=inventory_items,
            locations=locations,
            lots=lots,
            serials=serials,
            receipt_cost_evidence=costs,
        )
        ReceiptSerialPresencePolicy.ensure_receivable(lines=lines, presence=presence)
        posting = StockPosting.create_from_execution(
            identifier=posting_id,
            execution=execution.posting_snapshot(),
            posted_at=now,
            positions=tuple(position.snapshot() for position in positions),
            inventory_items=tuple(item.tracking_snapshot() for item in inventory_items),
            lots=lots,
            serials=serials,
            locations=locations,
            entry_bindings=entry_bindings,
        )
        items = {item.inventory_item_id: item for item in inventory_items}
        by_location = {location.id: location for location in locations}
        by_lot = {lot.id: lot for lot in lots}
        by_serial = {serial.id: serial for serial in serials}
        entries = {entry.position_id: entry for entry in posting.entries}
        after = tuple(
            position.apply_posting_entry(
                entries[position.id].snapshot(),
                expected_version=position.version,
                inventory_item=items[
                    position.dimensions.inventory_item_id
                ].stock_snapshot(),
                location=by_location[position.dimensions.location_id],
                warehouse=warehouse,
                lot=by_lot.get(position.dimensions.lot_id) if position.dimensions.lot_id is not None else None,
                serial=by_serial.get(position.dimensions.serial_id) if position.dimensions.serial_id is not None else None,
            )
            for position in positions
        )
        updated = document.register_execution(
            execution.snapshot_for_document(), updated_at=now
        )
        return ReceiptPostingResult(
            updated,
            execution,
            posting,
            positions,
            after,
            StockReceiptPosted(
                event_id,
                execution.id.uuid,
                posting.id.uuid,
                updated.id.uuid,
                updated.version,
                now,
            ),
        )
