from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_document.value_object.status_change_event_id import (
    StockStatusChangeEventIdVO,
)
from uuid import UUID
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.domain.stock_document.status_change_posting import (
    StatusChangePostingService,
)
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_serial.repository import (
    StockSerialRepositoryProtocol,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.status_change_route import (
    StatusChangeExecutionRouteVO,
)
from src.modules.inventory.domain.stock_position.repository import (
    StockPositionRepositoryProtocol,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.inventory.domain.stock_position.error import StockPositionNotFoundError


from dataclasses import dataclass
from decimal import Decimal
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.inventory_item.execution_snapshot import (
    InventoryItemExecutionSnapshot,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from datetime import datetime
from src.modules.inventory.domain.stock_document.status_change_posting import (
    StatusChangePostingResult,
)


@dataclass(frozen=True, slots=True)
class StatusChangeFactLine:
    """Передаёт общий вход чистой подготовки без actor, ключа и транспорта."""

    client_line_id: UUID
    document_line_id: UUID
    source_position_id: UUID
    quantity: Decimal
    uom: str


@dataclass(frozen=True, slots=True)
class StatusChangeFacts:
    """Фиксирует документ, ожидаемую версию и выбранные распределения."""

    document_id: UUID
    expected_version: int
    lines: tuple[StatusChangeFactLine, ...]


@dataclass(frozen=True, slots=True)
class StatusChangePostingContext:
    """Объединяет бизнес-снимки для одного расчёта, не раскрывая ORM или SQL-сессию."""

    document: StockDocument
    warehouse: WarehouseSnapshot
    inventory_items: tuple[InventoryItemExecutionSnapshot, ...]
    locations: tuple[StockLocationSnapshot, ...]
    lots: tuple[StockLotSnapshot, ...]
    serials: tuple[StockSerialSnapshot, ...]
    positions: tuple[StockPosition, ...]
    lines: tuple[StockExecutionLine, ...]
    presence: tuple[StockSerialPresenceSnapshot, ...]
    new_position_ids: frozenset[StockPositionIdVO]
    location_codes: dict[UUID, str]
    lot_numbers: dict[UUID, str]
    serial_numbers: dict[UUID, str]


class StatusChangeContextLoader:
    """Загружает одинаковый бизнес-контекст для preview и атомарного проведения."""

    def __init__(
        self,
        documents: StockDocumentRepositoryProtocol,
        warehouses: WarehouseRepositoryProtocol,
        items: InventoryItemRepositoryProtocol,
        locations: StockLocationRepositoryProtocol,
        serials: StockSerialRepositoryProtocol,
        lots: StockLotRepositoryProtocol,
        positions: StockPositionRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает порты общего UoW и генератор серверных идентичностей."""
        self._documents, self._warehouses, self._items = documents, warehouses, items
        self._locations, self._serials, self._lots = locations, serials, lots
        self._positions, self._uuid = positions, uuid

    async def load(
        self, request: StatusChangeFacts, *, lock: bool
    ) -> StatusChangePostingContext:
        """При проведении блокирует корни и создаёт нули; preview использует только обычное чтение."""
        document = await (
            self._documents.get_for_update if lock else self._documents.get
        )(StockDocumentIdVO(request.document_id))
        if document is None:
            raise StockDocumentNotFoundError("Документ изменения состояния не найден.")
        document.ensure_version(request.expected_version)
        document.ensure_manual_status_change()
        document.execution_snapshot()
        warehouse = await (
            self._warehouses.get_for_share if lock else self._warehouses.get
        )(document.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        planned = {
            value.client_line_id: document.get_line(
                StockDocumentLineIdVO(value.document_line_id)
            )
            for value in request.lines
        }
        items = {}
        for identifier in sorted(
            {line.inventory_item_id.uuid for line in planned.values()}
        ):
            item = await (self._items.get_for_update if lock else self._items.get)(
                InventoryItemIdVO(identifier)
            )
            if item is None:
                raise InventoryItemNotFoundError("SKU строки не найден.")
            items[item.id] = item
        sources = {}
        for identifier in sorted({value.source_position_id for value in request.lines}):
            position = await self._positions.get(StockPositionIdVO(identifier))
            if position is None:
                raise StockPositionNotFoundError("Исходная позиция не найдена.")
            sources[identifier] = position
        for value in request.lines:
            StatusChangePostingService.ensure_source(
                document,
                sources[value.source_position_id],
                planned[value.client_line_id].id,
            )
        locations = {}
        location_codes: dict[UUID, str] = {}
        for identifier in sorted(
            {position.dimensions.location_id.uuid for position in sources.values()}
        ):
            location = (
                await self._locations.get_for_update(
                    StockLocationIdVO(identifier), warehouse_id=document.warehouse_id
                )
                if lock
                else await self._locations.get(StockLocationIdVO(identifier))
            )
            if location is None:
                raise StockLocationNotFoundError(
                    "Локация источника не найдена в складе документа."
                )
            locations[location.id] = location.snapshot()
            location_codes[identifier] = location.code.value
        serials = {}
        serial_numbers: dict[UUID, str] = {}
        for identifier in sorted(
            {
                p.dimensions.serial_id.uuid
                for p in sources.values()
                if p.dimensions.serial_id is not None
            }
        ):
            source = next(
                p
                for p in sources.values()
                if p.dimensions.serial_id is not None
                and p.dimensions.serial_id.uuid == identifier
            )
            serial = await (
                self._serials.get_for_update if lock else self._serials.get
            )(
                StockSerialIdVO(identifier),
                inventory_item_id=source.dimensions.inventory_item_id,
            )
            if serial is None:
                raise StockSerialNotFoundError("Серия источника не найдена.")
            serials[serial.id] = serial.snapshot()
            serial_numbers[identifier] = serial.number.value
        lots = {}
        lot_numbers: dict[UUID, str] = {}
        for identifier in sorted(
            {
                p.dimensions.lot_id.uuid
                for p in sources.values()
                if p.dimensions.lot_id is not None
            }
        ):
            source = next(
                p
                for p in sources.values()
                if p.dimensions.lot_id is not None
                and p.dimensions.lot_id.uuid == identifier
            )
            lot = await (self._lots.get_for_update if lock else self._lots.get)(
                StockLotIdVO(identifier),
                inventory_item_id=source.dimensions.inventory_item_id,
            )
            if lot is None:
                raise StockLotNotFoundError("Партия источника не найдена.")
            lots[lot.id] = lot.snapshot()
            lot_numbers[identifier] = lot.number.value
        routes = {
            value.client_line_id: StatusChangeExecutionRouteVO.to_status(
                sources[value.source_position_id].dimensions,
                document.status_change_snapshot().target_status,
            )
            for value in request.lines
        }
        candidates = {source.dimensions: source for source in sources.values()}
        source_ids = {source.id for source in sources.values()}
        for route in routes.values():
            dims = route.destination
            if dims not in candidates:
                candidates[dims] = StockPosition.create(
                    identifier=StockPositionIdVO(self._uuid.new()),
                    dimensions=dims,
                    inventory_item=items[dims.inventory_item_id].stock_snapshot(),
                    location=locations[dims.location_id],
                    warehouse=warehouse.snapshot(),
                    lot=lots.get(dims.lot_id) if dims.lot_id else None,
                    serial=serials.get(dims.serial_id) if dims.serial_id else None,
                )
        positions = []
        new_ids: set[StockPositionIdVO] = set()
        for candidate in sorted(
            candidates.values(),
            key=lambda p: (
                p.dimensions.inventory_item_id.uuid.int,
                p.dimensions.location_id.uuid.int,
                p.dimensions.owner_id.uuid.int,
                p.dimensions.lot_id.uuid.int if p.dimensions.lot_id else -1,
                p.dimensions.serial_id.uuid.int if p.dimensions.serial_id else -1,
                p.dimensions.stock_status.value,
            ),
        ):
            if lock:
                position = (
                    await self._positions.get_for_update(candidate.id)
                    if candidate.id in source_ids
                    else await self._positions.get_or_add_for_update(candidate)
                )
            elif candidate.id in source_ids:
                position = await self._positions.get(candidate.id)
            else:
                position = await self._positions.get_by_dimensions(candidate.dimensions)
                if position is None:
                    position = candidate
                    new_ids.add(candidate.id)
            if position is None:
                raise StockPositionNotFoundError("Исходная позиция не найдена.")
            positions.append(position)
            if position.id in source_ids:
                sources[position.id.uuid] = position
        presence = await (
            self._positions.serial_presence
            if lock
            else self._positions.read_serial_presence
        )(tuple(sorted(serials, key=lambda v: v.uuid.int)))
        lines = []
        for value in request.lines:
            source = sources[value.source_position_id]
            StatusChangePostingService.ensure_source(
                document, source, planned[value.client_line_id].id
            )
            item = items[planned[value.client_line_id].inventory_item_id]
            lines.append(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(self._uuid.new()),
                    document_line_id=planned[value.client_line_id].id,
                    inventory_item=item.execution_snapshot(),
                    quantity=QuantityVO(value.quantity),
                    uom=UomCodeVO(value.uom),
                    route=routes[value.client_line_id],
                )
            )
        if not lock:
            # Двойное чтение версий даёт общую точку снимка без резервирования или блокировок.
            for position in positions:
                current = await self._positions.get_by_dimensions(position.dimensions)
                if position.id in new_ids:
                    if current is not None:
                        raise StockPositionVersionConflictError(
                            "Назначение изменилось во время расчёта. Обновите preview."
                        )
                elif current is None or current.version != position.version:
                    raise StockPositionVersionConflictError(
                        "Остатки изменились во время расчёта. Обновите preview."
                    )
            current_document = await self._documents.get(document.id)
            if current_document is None:
                raise StockDocumentNotFoundError("Документ не найден.")
            current_document.ensure_version(request.expected_version)
        return StatusChangePostingContext(
            document,
            warehouse.snapshot(),
            tuple(item.execution_snapshot() for item in items.values()),
            tuple(locations.values()),
            tuple(lots.values()),
            tuple(serials.values()),
            tuple(positions),
            tuple(lines),
            presence,
            frozenset(new_ids),
            location_codes,
            lot_numbers,
            serial_numbers,
        )


def calculate_status_change(
    context: StatusChangePostingContext, *, now: datetime, uuid: UUIdGeneratorProtocol
) -> StatusChangePostingResult:
    """Вызывает один Domain-расчёт; созданные в памяти факты preview никогда не сохраняются."""
    return StatusChangePostingService.post(
        document=context.document,
        expected_version=context.document.version,
        execution_id=StockExecutionIdVO(uuid.new()),
        posting_id=StockPostingIdVO(uuid.new()),
        event_id=StockStatusChangeEventIdVO(uuid.new()),
        lines=context.lines,
        positions=context.positions,
        warehouse=context.warehouse,
        inventory_items=context.inventory_items,
        locations=context.locations,
        lots=context.lots,
        serials=context.serials,
        entry_bindings=tuple(
            StockPostingEntryBindingVO(position.id, StockLedgerEntryIdVO(uuid.new()))
            for position in context.positions
        ),
        presence=context.presence,
        now=now,
    )
