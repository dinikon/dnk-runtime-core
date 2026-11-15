from src.modules.inventory.application.stock_document.command.post_status_change.command import (
    PostStatusChangeCommand,
)
from src.modules.inventory.application.stock_document.command.post_status_change.dto import (
    PostStatusChangeResultDTO,
)
from src.modules.inventory.application.stock_document.command.post_status_change.fingerprint import (
    status_change_posting_fingerprint,
)
from src.modules.inventory.application.stock_document.command.post_status_change.result_mapper import (
    status_change_result,
)
from src.modules.inventory.application.stock_document.port.status_change_posting import (
    StatusChangePostingRequestsPort,
)
from src.modules.inventory.application.stock_document.status_change_read_service import (
    StatusChangeDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.query import (
    GetStatusChangeDocumentQuery,
)
from src.modules.inventory.domain.stock_document.repository import (
    StockDocumentRepositoryProtocol,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    StatusChangePostingConflictError,
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


from src.modules.inventory.application.stock_document.status_change_context import (
    StatusChangeContextLoader,
    StatusChangeFacts,
    StatusChangeFactLine,
    calculate_status_change,
)


class PostStatusChangeHandler:
    """Координирует физическое изменение состояния на портах единственной внешней транзакции."""

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
        requests: StatusChangePostingRequestsPort,
        reader: StatusChangeDocumentReadService,
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
        self._loader = StatusChangeContextLoader(
            documents, warehouses, items, locations, serials, lots, positions, uuid
        )

    async def execute(
        self, command: PostStatusChangeCommand
    ) -> PostStatusChangeResultDTO:
        """Сохраняет исполнение, обе стороны Ledger, позиции, прогресс и событие атомарно."""
        fingerprint = status_change_posting_fingerprint(command)
        claim = await self._requests.claim(
            command.idempotency_key, fingerprint, command.actor_id, self._clock.now()
        )
        if claim.fingerprint != fingerprint:
            raise StatusChangePostingConflictError(
                "Ключ изменения состояния уже использован для другого состава."
            )
        if not claim.is_new:
            if claim.result is None:
                raise RuntimeError("Завершённая команда не содержит результата.")
            return claim.result
        context = await self._loader.load(
            StatusChangeFacts(
                command.document_id,
                command.expected_version,
                tuple(
                    StatusChangeFactLine(
                        v.client_line_id,
                        v.document_line_id,
                        v.source_position_id,
                        v.quantity,
                        v.uom,
                    )
                    for v in command.lines
                ),
            ),
            lock=True,
        )
        bundle = calculate_status_change(
            context, now=self._clock.now(), uuid=self._uuid
        )
        document = context.document
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
        header = await self._reader.get(GetStatusChangeDocumentQuery(document.id.uuid))
        result = status_change_result(
            command=command,
            bundle=bundle,
            header=header,
            location_codes=context.location_codes,
            lot_numbers=context.lot_numbers,
            serial_numbers=context.serial_numbers,
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
                event_type="inventory.stock_status_change_posted",
                event_version=1,
                aggregate_type="StockPosting",
                aggregate_id=event.posting_id.uuid,
                occurred_at=event.occurred_at,
                payload={
                    "document_id": str(event.document_id.uuid),
                    "reason": result.reason,
                    "target_status": result.target_status,
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
