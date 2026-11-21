from dataclasses import replace
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnOriginSnapshot,
    StockReturnUsageSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.return_direction import (
    ReturnDirection,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
)
from src.modules.inventory.application.stock_document.port.return_origin import (
    ReturnOriginPort,
)
from src.modules.inventory.domain.policy.stock_return import StockReturnPolicy
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_document.value_object.return_event_id import (
    StockReturnEventIdVO,
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
from src.modules.inventory.domain.stock_document.return_posting import (
    ReturnPostingService,
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
from src.modules.inventory.domain.stock_execution.value_object.return_receipt_route import (
    ReturnReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.return_issue_route import (
    ReturnIssueExecutionRouteVO,
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
from src.modules.inventory.domain.stock_document.return_posting import (
    ReturnPostingResult,
)


@dataclass(frozen=True, slots=True)
class ReturnFactLine:
    """Передаёт общий вход чистой подготовки без actor, ключа и транспорта."""

    client_line_id: UUID
    document_line_id: UUID
    quantity: Decimal
    uom: str
    source_position_id: UUID | None = None
    location_id: UUID | None = None
    stock_status: str | None = None


@dataclass(frozen=True, slots=True)
class ReturnFacts:
    """Фиксирует документ, ожидаемую версию и выбранные распределения."""

    document_id: UUID
    expected_version: int
    lines: tuple[ReturnFactLine, ...]


@dataclass(frozen=True, slots=True)
class ReturnPostingContext:
    """Объединяет бизнес-снимки для одного расчёта, не раскрывая ORM или SQL-сессию."""

    document: StockDocument
    origin: StockReturnOriginSnapshot
    usage: tuple[StockReturnUsageSnapshot, ...]
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


class ReturnContextLoader:
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
        origin: ReturnOriginPort,
    ) -> None:
        """Получает порты общего UoW и генератор серверных идентичностей."""
        self._documents, self._warehouses, self._items = documents, warehouses, items
        self._locations, self._serials, self._lots = locations, serials, lots
        self._positions, self._uuid = positions, uuid
        self._origin = origin

    async def load(self, request: ReturnFacts, *, lock: bool) -> ReturnPostingContext:
        """При проведении блокирует корни и создаёт нули; preview использует только обычное чтение."""
        document = await (
            self._documents.get_for_update if lock else self._documents.get
        )(StockDocumentIdVO(request.document_id))
        if document is None:
            raise StockDocumentNotFoundError("Документ возврата не найден.")
        document.ensure_version(request.expected_version)
        document.ensure_manual_return()
        document.execution_snapshot()
        if document.return_details is None:
            raise InvalidStockReturnError("Нет основания возврата.")
        origin = await self._origin.get(
            document.return_details.origin_execution_id, lock=lock
        )
        if origin is None:
            raise StockDocumentNotFoundError("Исходное исполнение не найдено.")
        StockReturnPolicy.ensure_details(document.return_details, origin)
        usage = await self._origin.usage(origin.id)
        incoming = document.return_details.direction is ReturnDirection.FROM_RECIPIENT
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
        for identifier in sorted(
            {
                value.source_position_id
                for value in request.lines
                if value.source_position_id is not None
            }
        ):
            position = await self._positions.get(StockPositionIdVO(identifier))
            if position is None:
                raise StockPositionNotFoundError("Исходная позиция не найдена.")
            sources[identifier] = position
        routes = {}
        for value in request.lines:
            plan = planned[value.client_line_id]
            if plan.return_origin_line_id is None:
                raise InvalidStockReturnError("Строка плана не имеет исходного факта.")
            source = StockReturnPolicy.line(origin, plan.return_origin_line_id)
            if incoming:
                if (
                    value.source_position_id is not None
                    or value.location_id is None
                    or value.stock_status is None
                ):
                    raise InvalidStockReturnError(
                        "Возврат от получателя требует адрес и состояние приёмки."
                    )
                dims = replace(
                    source.dimensions,
                    location_id=StockLocationIdVO(value.location_id),
                    stock_status=StockStatus(value.stock_status),
                )
                routes[value.client_line_id] = ReturnReceiptExecutionRouteVO(
                    source.id, dims
                )
            else:
                if (
                    value.source_position_id is None
                    or value.location_id is not None
                    or value.stock_status is not None
                ):
                    raise InvalidStockReturnError(
                        "Возврат поставщику требует существующую исходную позицию."
                    )
                routes[value.client_line_id] = ReturnIssueExecutionRouteVO(
                    source.id, sources[value.source_position_id].dimensions
                )
        dimensions = {route.dimensions[0] for route in routes.values()}
        locations = {}
        location_codes: dict[UUID, str] = {}
        for identifier in sorted({d.location_id.uuid for d in dimensions}):
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
            {d.serial_id.uuid for d in dimensions if d.serial_id is not None}
        ):
            dims = next(
                d
                for d in dimensions
                if d.serial_id is not None and d.serial_id.uuid == identifier
            )
            serial = await (
                self._serials.get_for_update if lock else self._serials.get
            )(StockSerialIdVO(identifier), inventory_item_id=dims.inventory_item_id)
            if serial is None:
                raise StockSerialNotFoundError("Серия основания не найдена.")
            serials[serial.id] = serial.snapshot()
            serial_numbers[identifier] = serial.number.value
        lots = {}
        lot_numbers: dict[UUID, str] = {}
        for identifier in sorted(
            {d.lot_id.uuid for d in dimensions if d.lot_id is not None}
        ):
            dims = next(
                d
                for d in dimensions
                if d.lot_id is not None and d.lot_id.uuid == identifier
            )
            lot = await (self._lots.get_for_update if lock else self._lots.get)(
                StockLotIdVO(identifier), inventory_item_id=dims.inventory_item_id
            )
            if lot is None:
                raise StockLotNotFoundError("Партия основания не найдена.")
            lots[lot.id] = lot.snapshot()
            lot_numbers[identifier] = lot.number.value
        candidates = {source.dimensions: source for source in sources.values()}
        source_ids = {source.id for source in sources.values()}
        if incoming:
            for dims in dimensions:
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
        return ReturnPostingContext(
            document,
            origin,
            usage,
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


def calculate_return(
    context: ReturnPostingContext, *, now: datetime, uuid: UUIdGeneratorProtocol
) -> ReturnPostingResult:
    """Вызывает один Domain-расчёт; созданные в памяти факты preview никогда не сохраняются."""
    return ReturnPostingService.post(
        document=context.document,
        expected_version=context.document.version,
        execution_id=StockExecutionIdVO(uuid.new()),
        posting_id=StockPostingIdVO(uuid.new()),
        event_id=StockReturnEventIdVO(uuid.new()),
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
        origin=context.origin,
        usage=context.usage,
        now=now,
    )
