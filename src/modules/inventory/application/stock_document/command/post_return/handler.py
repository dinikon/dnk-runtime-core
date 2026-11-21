from src.modules.inventory.application.stock_document.port.return_origin import (
    ReturnOriginPort,
)
from src.modules.inventory.application.stock_document.command.post_return.command import (
    PostReturnCommand,
)
from src.modules.inventory.application.stock_document.command.post_return.dto import (
    PostReturnResultDTO,
)
from src.modules.inventory.application.stock_document.command.post_return.fingerprint import (
    return_posting_fingerprint,
)
from src.modules.inventory.application.stock_document.command.post_return.result_mapper import (
    return_result,
)
from src.modules.inventory.application.stock_document.port.return_posting import (
    ReturnPostingRequestsPort,
)
from src.modules.inventory.application.stock_document.return_read_service import (
    ReturnDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
)
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnPostingConflictError,
)
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.stock_serial.repository import (
    StockSerialRepositoryProtocol,
)
from src.modules.inventory.domain.stock_lot.repository import StockLotRepositoryProtocol
from src.modules.inventory.domain.stock_execution.repository import (
    StockExecutionRepositoryProtocol,
)
from src.modules.inventory.domain.stock_position.repository import (
    StockPositionRepositoryProtocol,
)
from src.modules.inventory.domain.stock_posting.repository import (
    StockPostingRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)
from src.modules.shared.domain.events.integration_event import IntegrationEvent


from src.modules.inventory.application.stock_document.return_context import (
    ReturnContextLoader,
    ReturnFacts,
    ReturnFactLine,
    calculate_return,
)


class PostReturnHandler:
    """Координирует физический возврат на портах единственной внешней транзакции."""

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
        requests: ReturnPostingRequestsPort,
        reader: ReturnDocumentReadService,
        outbox: OutboxRepositoryProtocol,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        origin: ReturnOriginPort,
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
        self._loader = ReturnContextLoader(
            documents,
            warehouses,
            items,
            locations,
            serials,
            lots,
            positions,
            uuid,
            origin,
        )

    async def execute(self, command: PostReturnCommand) -> PostReturnResultDTO:
        """Сохраняет исполнение, Ledger, позиции, прогресс и событие атомарно."""
        fingerprint = return_posting_fingerprint(command)
        claim = await self._requests.claim(
            command.idempotency_key, fingerprint, command.actor_id, self._clock.now()
        )
        if claim.fingerprint != fingerprint:
            raise ReturnPostingConflictError(
                "Ключ возврата уже использован для другого состава."
            )
        if not claim.is_new:
            if claim.result is None:
                raise RuntimeError("Завершённая команда не содержит результата.")
            return claim.result
        context = await self._loader.load(
            ReturnFacts(
                command.document_id,
                command.expected_version,
                tuple(
                    ReturnFactLine(
                        client_line_id=v.client_line_id,
                        document_line_id=v.document_line_id,
                        source_position_id=v.source_position_id,
                        quantity=v.quantity,
                        uom=v.uom,
                        location_id=v.location_id,
                        stock_status=v.stock_status,
                    )
                    for v in command.lines
                ),
            ),
            lock=True,
        )
        bundle = calculate_return(context, now=self._clock.now(), uuid=self._uuid)
        document = context.document
        await self._executions.add(bundle.execution)
        await self._postings.add(bundle.posting)
        entries = {entry.position_id: entry for entry in bundle.posting.entries}
        # Блокировки позиций уже получены в общем каноническом порядке.
        transitions = sorted(
            zip(bundle.before, bundle.after, strict=True),
            key=lambda pair: entries[pair[0].id].quantity_delta.value > 0,
        )
        for before, after in transitions:
            await self._positions.save(after, expected_version=before.version)
        await self._documents.save(
            bundle.document, expected_version=command.expected_version
        )
        header = await self._reader.get(GetReturnDocumentQuery(document.id.uuid))
        result = return_result(
            command=command,
            bundle=bundle,
            header=header,
            location_codes=context.location_codes,
            lot_numbers=context.lot_numbers,
            serial_numbers=context.serial_numbers,
        )
        role = "DESTINATION" if result.direction == "FROM_RECIPIENT" else "SOURCE"
        await self._requests.add_links(
            tuple((line.id, line.ledger_entry_id, role) for line in result.lines)
        )
        event = bundle.event
        await self._outbox.add(
            IntegrationEvent(
                event_id=event.event_id.uuid,
                tenant_id=command.tenant_id,
                event_type="inventory.stock_return_posted",
                event_version=1,
                aggregate_type="StockPosting",
                aggregate_id=event.posting_id.uuid,
                occurred_at=event.occurred_at,
                payload={
                    "document_id": str(event.document_id.uuid),
                    "reason": result.reason,
                    "direction": result.direction,
                    "origin_execution_id": str(result.origin_execution_id),
                    "lines": [
                        {
                            "execution_line_id": str(line.id),
                            "origin_execution_line_id": str(
                                line.origin_execution_line_id
                            ),
                            "quantity": str(line.quantity),
                            "base_uom": line.base_uom,
                        }
                        for line in result.lines
                    ],
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
