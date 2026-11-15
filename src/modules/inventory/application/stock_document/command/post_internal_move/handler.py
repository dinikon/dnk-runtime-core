from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_document.value_object.internal_move_event_id import (
    StockInternalMoveEventIdVO,
)
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_internal_move.command import (
    PostInternalMoveCommand,
)
from src.modules.inventory.application.stock_document.command.post_internal_move.dto import (
    PostInternalMoveResultDTO,
)
from src.modules.inventory.application.stock_document.command.post_internal_move.fingerprint import (
    internal_move_posting_fingerprint,
)
from src.modules.inventory.application.stock_document.command.post_internal_move.result_mapper import (
    internal_move_result,
)
from src.modules.inventory.application.stock_document.port.internal_move_posting import (
    InternalMovePostingRequestsPort,
)
from src.modules.inventory.application.stock_document.internal_move_read_service import (
    InternalMoveDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.query import (
    GetInternalMoveDocumentQuery,
)
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
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMovePostingConflictError,
)
from src.modules.inventory.domain.stock_document.internal_move_posting import (
    InternalMovePostingService,
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
from src.modules.inventory.domain.stock_execution.repository import (
    StockExecutionRepositoryProtocol,
)
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_position.repository import (
    StockPositionRepositoryProtocol,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.repository import (
    StockPostingRepositoryProtocol,
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
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)
from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.inventory.domain.stock_position.error import StockPositionNotFoundError


class PostInternalMoveHandler:
    """Координирует физический перемещение на портах единственной внешней транзакции."""

    def __init__(
        self,
        documents: StockDocumentRepositoryProtocol,
        warehouses: WarehouseRepositoryProtocol,
        items: InventoryItemRepositoryProtocol,
        locations: StockLocationRepositoryProtocol,
        serials: StockSerialRepositoryProtocol,
        lots: StockLotRepositoryProtocol,
        positions: StockPositionRepositoryProtocol,
        executions: StockExecutionRepositoryProtocol,
        postings: StockPostingRepositoryProtocol,
        requests: InternalMovePostingRequestsPort,
        reader: InternalMoveDocumentReadService,
        outbox: OutboxRepositoryProtocol,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает необходимые порты общего tenant-UoW без инфраструктурной сессии."""
        self._documents, self._warehouses, self._items = documents, warehouses, items
        self._locations, self._serials, self._lots = locations, serials, lots
        self._positions, self._executions, self._postings = (
            positions,
            executions,
            postings,
        )
        self._requests, self._reader, self._outbox = requests, reader, outbox
        self._clock, self._uuid = clock, uuid

    async def execute(
        self, command: PostInternalMoveCommand
    ) -> PostInternalMoveResultDTO:
        """Сохраняет исполнение, обе стороны Ledger, позиции, прогресс и событие атомарно."""
        fingerprint = internal_move_posting_fingerprint(command)
        claim = await self._requests.claim(
            command.idempotency_key, fingerprint, command.actor_id, self._clock.now()
        )
        if claim.fingerprint != fingerprint:
            raise InternalMovePostingConflictError(
                "Ключ перемещения уже использован для другого состава."
            )
        if not claim.is_new:
            if claim.result is None:
                raise RuntimeError("Завершённая команда не содержит результата.")
            return claim.result
        document = await self._documents.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ перемещения не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_internal_move()
        document.execution_snapshot()
        warehouse = await self._warehouses.get_for_share(document.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        planned = {
            value.client_line_id: document.get_line(
                StockDocumentLineIdVO(value.document_line_id)
            )
            for value in command.lines
        }
        items = {}
        for identifier in sorted(
            {line.inventory_item_id.uuid for line in planned.values()}
        ):
            item = await self._items.get_for_update(InventoryItemIdVO(identifier))
            if item is None:
                raise InventoryItemNotFoundError("SKU строки не найден.")
            items[item.id] = item
        sources = {}
        for identifier in sorted({value.source_position_id for value in command.lines}):
            position = await self._positions.get(StockPositionIdVO(identifier))
            if position is None:
                raise StockPositionNotFoundError("Исходная позиция не найдена.")
            sources[identifier] = position
        for value in command.lines:
            InternalMovePostingService.ensure_source(
                document,
                sources[value.source_position_id],
                planned[value.client_line_id].id,
            )
        locations = {}
        location_codes: dict[UUID, str] = {}
        for identifier in sorted(
            {position.dimensions.location_id.uuid for position in sources.values()}
            | {value.destination_location_id for value in command.lines}
        ):
            location = await self._locations.get_for_update(
                StockLocationIdVO(identifier), warehouse_id=document.warehouse_id
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
            serial = await self._serials.get_for_update(
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
            lot = await self._lots.get_for_update(
                StockLotIdVO(identifier),
                inventory_item_id=source.dimensions.inventory_item_id,
            )
            if lot is None:
                raise StockLotNotFoundError("Партия источника не найдена.")
            lots[lot.id] = lot.snapshot()
            lot_numbers[identifier] = lot.number.value
        routes = {
            value.client_line_id: InternalMoveExecutionRouteVO.to_location(
                sources[value.source_position_id].dimensions,
                StockLocationIdVO(value.destination_location_id),
            )
            for value in command.lines
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
            position = (
                await self._positions.get_for_update(candidate.id)
                if candidate.id in source_ids
                else await self._positions.get_or_add_for_update(candidate)
            )
            if position is None:
                raise StockPositionNotFoundError("Исходная позиция не найдена.")
            positions.append(position)
            if position.id in source_ids:
                sources[position.id.uuid] = position
        presence = await self._positions.serial_presence(
            tuple(sorted(serials, key=lambda v: v.uuid.int))
        )
        lines = []
        for value in command.lines:
            source = sources[value.source_position_id]
            InternalMovePostingService.ensure_source(
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
        bundle = InternalMovePostingService.post(
            document=document,
            expected_version=command.expected_version,
            execution_id=StockExecutionIdVO(self._uuid.new()),
            posting_id=StockPostingIdVO(self._uuid.new()),
            event_id=StockInternalMoveEventIdVO(self._uuid.new()),
            lines=tuple(lines),
            positions=tuple(positions),
            warehouse=warehouse.snapshot(),
            inventory_items=tuple(item.execution_snapshot() for item in items.values()),
            locations=tuple(locations.values()),
            lots=tuple(lots.values()),
            serials=tuple(serials.values()),
            entry_bindings=tuple(
                StockPostingEntryBindingVO(
                    position.id, StockLedgerEntryIdVO(self._uuid.new())
                )
                for position in positions
            ),
            presence=presence,
            now=self._clock.now(),
        )
        await self._executions.add(bundle.execution)
        await self._postings.add(bundle.posting)
        entries = {entry.position_id: entry for entry in bundle.posting.entries}
        # Блокировки уже получены в общем порядке. SERIAL освобождает источник до записи назначения.
        transitions = sorted(
            zip(bundle.before, bundle.after, strict=True),
            key=lambda pair: entries[pair[0].id].quantity_delta.value > 0,
        )
        for before, after in transitions:
            await self._positions.save(after, expected_version=before.version)
        await self._documents.save(
            bundle.document, expected_version=command.expected_version
        )
        header = await self._reader.get(GetInternalMoveDocumentQuery(document.id.uuid))
        result = internal_move_result(
            command=command,
            bundle=bundle,
            header=header,
            location_codes=location_codes,
            lot_numbers=lot_numbers,
            serial_numbers=serial_numbers,
        )
        await self._requests.add_links(
            tuple(
                link
                for line in result.lines
                for link in (
                    (line.id, line.ledger_entry_id, "SOURCE"),
                    (line.id, line.destination_ledger_entry_id, "DESTINATION"),
                )
            )
        )
        event = bundle.event
        await self._outbox.add(
            IntegrationEvent(
                event_id=event.event_id.uuid,
                tenant_id=command.tenant_id,
                event_type="inventory.stock_internal_move_posted",
                event_version=1,
                aggregate_type="StockPosting",
                aggregate_id=event.posting_id.uuid,
                occurred_at=event.occurred_at,
                payload={
                    "document_id": str(event.document_id.uuid),
                    "execution_id": str(event.execution_id.uuid),
                    "posting_id": str(event.posting_id.uuid),
                    "document_version": event.document_version,
                    "positions": [
                        {
                            "id": str(p.id),
                            "delta": str(p.delta),
                            "base_uom": p.base_uom,
                            "version": p.after_version,
                        }
                        for p in result.positions
                    ],
                },
            )
        )
        await self._requests.complete(command.idempotency_key, result)
        return result
