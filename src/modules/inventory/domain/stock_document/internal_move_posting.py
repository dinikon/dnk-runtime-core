from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentContextError,
)
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InsufficientInternalMoveStockError,
)
from src.modules.inventory.domain.error import NegativeStockQuantityError
from src.modules.inventory.domain.stock_posting.ledger_entry_snapshot import (
    StockLedgerEntrySnapshot,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.policy.internal_move_serial_presence import (
    InternalMoveSerialPresencePolicy,
)
from dataclasses import dataclass
from datetime import datetime
from src.modules.inventory.domain.stock_document.value_object.internal_move_event_id import (
    StockInternalMoveEventIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
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
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


@dataclass(frozen=True, slots=True)
class StockInternalMovePosted:
    """Доменный факт согласованного изменения документа, позиций и физического журнала."""

    event_id: StockInternalMoveEventIdVO
    execution_id: StockExecutionIdVO
    posting_id: StockPostingIdVO
    document_id: StockDocumentIdVO
    document_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class InternalMovePostingResult:
    """Передаёт чистый согласованный результат нескольких агрегатов, не владея их жизненными циклами."""

    document: StockDocument
    execution: StockExecution
    posting: StockPosting
    before: tuple[StockPosition, ...]
    after: tuple[StockPosition, ...]
    event: StockInternalMovePosted


class InternalMovePostingService:
    """Строит полный результат перемещения без SQL, репозиториев и управления транзакцией."""

    @staticmethod
    def post(
        *,
        document: StockDocument,
        expected_version: int,
        execution_id: StockExecutionIdVO,
        posting_id: StockPostingIdVO,
        event_id: StockInternalMoveEventIdVO,
        lines: tuple[StockExecutionLine, ...],
        positions: tuple[StockPosition, ...],
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemExecutionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        lots: tuple[StockLotSnapshot, ...],
        serials: tuple[StockSerialSnapshot, ...],
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
        now: datetime,
    ) -> InternalMovePostingResult:
        """Проверяет факт и присутствие, строит Ledger, применяет каждую запись один раз и регистрирует прогресс."""
        document.ensure_version(expected_version)
        document.ensure_manual_internal_move()
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
        )
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
        changed = tuple(
            InternalMovePostingService._apply(
                position,
                entries[position.id].snapshot(),
                expected_version=position.version,
                inventory_item=items[
                    position.dimensions.inventory_item_id
                ].stock_snapshot(),
                location=by_location[position.dimensions.location_id],
                warehouse=warehouse,
                lot=(
                    by_lot.get(position.dimensions.lot_id)
                    if position.dimensions.lot_id is not None
                    else None
                ),
                serial=(
                    by_serial.get(position.dimensions.serial_id)
                    if position.dimensions.serial_id is not None
                    else None
                ),
            )
            for position in sorted(
                positions,
                key=lambda position: entries[position.id].quantity_delta.value > 0,
            )
        )
        by_id = {position.id: position for position in changed}
        after = tuple(by_id[position.id] for position in positions)
        InternalMoveSerialPresencePolicy.ensure_movable(
            lines=lines, positions=positions, presence=presence
        )
        updated = document.register_execution(
            execution.snapshot_for_document(), updated_at=now
        )
        return InternalMovePostingResult(
            updated,
            execution,
            posting,
            positions,
            after,
            StockInternalMovePosted(
                event_id,
                execution.id,
                posting.id,
                updated.id,
                updated.version,
                now,
            ),
        )

    @staticmethod
    def ensure_source(
        document: StockDocument, position: StockPosition, line_id: StockDocumentLineIdVO
    ) -> None:
        """Требует тот же SKU и владельца; склад источника проверяется по снимку локации."""
        line = document.get_line(line_id)
        if (
            position.dimensions.inventory_item_id != line.inventory_item_id
            or position.dimensions.owner_id != document.owner_id
        ):
            raise InvalidStockDocumentContextError(
                "Исходная позиция должна соответствовать SKU строки и владельцу документа."
            )

    @staticmethod
    def _apply(
        position: StockPosition,
        entry: StockLedgerEntrySnapshot,
        *,
        expected_version: int,
        inventory_item: InventoryItemStockSnapshot,
        location: StockLocationSnapshot,
        warehouse: WarehouseSnapshot,
        lot: StockLotSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
    ) -> StockPosition:
        """Добавляет адресный контекст к доменному запрету отрицательного физического остатка."""
        try:
            return position.apply_posting_entry(
                entry,
                expected_version=expected_version,
                inventory_item=inventory_item,
                location=location,
                warehouse=warehouse,
                lot=lot,
                serial=serial,
            )
        except NegativeStockQuantityError as exc:
            raise InsufficientInternalMoveStockError(
                "Недостаточно физического количества в выбранной позиции.",
                position_id=position.id,
                requested=QuantityVO(entry.quantity_delta.value.copy_abs()),
                current=position.on_hand_qty,
                base_uom=position.base_uom,
            ) from exc
