from src.modules.inventory.domain.stock_document.value_object.write_off_event_id import (
    StockWriteOffEventIdVO,
)
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_write_off.command import (
    PostWriteOffCommand,
)
from src.modules.inventory.application.stock_document.command.post_write_off.dto import (
    PostWriteOffResultDTO,
)
from src.modules.inventory.application.stock_document.command.post_write_off.fingerprint import (
    write_off_posting_fingerprint,
)
from src.modules.inventory.application.stock_document.command.post_write_off.result_mapper import (
    write_off_result,
)
from src.modules.inventory.application.stock_document.port.write_off_posting import (
    WriteOffPostingRequestsPort,
)
from src.modules.inventory.application.stock_document.write_off_read_service import (
    WriteOffDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
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
from src.modules.inventory.domain.stock_document.write_off_error import (
    WriteOffPostingConflictError,
)
from src.modules.inventory.domain.stock_document.write_off_posting import (
    WriteOffPostingService,
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
from src.modules.inventory.domain.stock_execution.value_object.write_off_route import (
    WriteOffExecutionRouteVO,
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


class PostWriteOffHandler:
    """Координирует физический списание на портах единственной внешней транзакции."""

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
        requests: WriteOffPostingRequestsPort,
        reader: WriteOffDocumentReadService,
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

    async def execute(self, command: PostWriteOffCommand) -> PostWriteOffResultDTO:
        """Сохраняет исполнение, отрицательный Ledger, позиции, прогресс и событие атомарно."""
        fingerprint = write_off_posting_fingerprint(command)
        claim = await self._requests.claim(
            command.idempotency_key, fingerprint, command.actor_id, self._clock.now()
        )
        if claim.fingerprint != fingerprint:
            raise WriteOffPostingConflictError(
                "Ключ списания уже использован для другого состава."
            )
        if not claim.is_new:
            if claim.result is None:
                raise RuntimeError("Завершённая команда не содержит результата.")
            return claim.result
        document = await self._documents.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ списания не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_write_off()
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
            WriteOffPostingService.ensure_source(
                document,
                sources[value.source_position_id],
                planned[value.client_line_id].id,
            )
        locations = {}
        location_codes: dict[UUID, str] = {}
        for identifier in sorted(
            {position.dimensions.location_id.uuid for position in sources.values()}
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
        positions = []
        for source in sorted(
            sources.values(),
            key=lambda p: (
                p.dimensions.inventory_item_id.uuid.int,
                p.dimensions.location_id.uuid.int,
                p.dimensions.owner_id.uuid.int,
                p.dimensions.lot_id.uuid.int if p.dimensions.lot_id else -1,
                p.dimensions.serial_id.uuid.int if p.dimensions.serial_id else -1,
                p.dimensions.stock_status.value,
            ),
        ):
            position = await self._positions.get_for_update(source.id)
            if position is None:
                raise StockPositionNotFoundError("Исходная позиция не найдена.")
            positions.append(position)
            sources[position.id.uuid] = position
        lines = []
        for value in command.lines:
            source = sources[value.source_position_id]
            WriteOffPostingService.ensure_source(
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
                    route=WriteOffExecutionRouteVO(source.dimensions),
                )
            )
        bundle = WriteOffPostingService.post(
            document=document,
            expected_version=command.expected_version,
            execution_id=StockExecutionIdVO(self._uuid.new()),
            posting_id=StockPostingIdVO(self._uuid.new()),
            event_id=StockWriteOffEventIdVO(self._uuid.new()),
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
            now=self._clock.now(),
        )
        await self._executions.add(bundle.execution)
        await self._postings.add(bundle.posting)
        for before, after in zip(bundle.before, bundle.after, strict=True):
            await self._positions.save(after, expected_version=before.version)
        await self._documents.save(
            bundle.document, expected_version=command.expected_version
        )
        header = await self._reader.get(GetWriteOffDocumentQuery(document.id.uuid))
        result = write_off_result(
            command=command,
            bundle=bundle,
            header=header,
            location_codes=location_codes,
            lot_numbers=lot_numbers,
            serial_numbers=serial_numbers,
        )
        await self._requests.add_links(
            tuple((line.id, line.ledger_entry_id) for line in result.lines)
        )
        event = bundle.event
        await self._outbox.add(
            IntegrationEvent(
                event_id=event.event_id.uuid,
                tenant_id=command.tenant_id,
                event_type="inventory.stock_write_off_posted",
                event_version=1,
                aggregate_type="StockPosting",
                aggregate_id=event.posting_id.uuid,
                occurred_at=event.occurred_at,
                payload={
                    "document_id": str(event.document_id.uuid),
                    "reason": result.reason,
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
