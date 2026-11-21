from src.modules.inventory.domain.stock_execution.value_object.receipt_cost_evidence_id import (
    ReceiptCostEvidenceIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.receipt_event_id import (
    StockReceiptEventIdVO,
)
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_receipt.command import (
    PostReceiptCommand,
)
from src.modules.inventory.application.stock_document.command.post_receipt.dto import (
    PostReceiptResultDTO,
)
from src.modules.inventory.application.stock_document.command.post_receipt.fingerprint import (
    receipt_posting_fingerprint,
)
from src.modules.inventory.application.stock_document.command.post_receipt.result_mapper import (
    receipt_result,
)
from src.modules.inventory.application.stock_document.port.receipt_posting import (
    ReceiptPostingRequestsPort,
    ReceiptCurrencyPort,
)
from src.modules.inventory.application.stock_document.read_service import (
    ReceiptDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.query import (
    GetReceiptDocumentQuery,
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
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptPostingConflictError,
)
from src.modules.inventory.domain.stock_document.receipt_posting import (
    ReceiptPostingService,
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
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.entity.receipt_cost_evidence import (
    ReceiptCostEvidence,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_cost_allocation import (
    ReceiptCostAllocationVO,
)
from src.modules.inventory.domain.stock_position.repository import (
    StockPositionRepositoryProtocol,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
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
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)
from src.modules.shared.domain.events.integration_event import IntegrationEvent


class PostReceiptHandler:
    """Координирует только порты и Domain; все записи принадлежат внешнему UoW."""

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
        requests: ReceiptPostingRequestsPort,
        currencies: ReceiptCurrencyPort,
        reader: ReceiptDocumentReadService,
        outbox: OutboxRepositoryProtocol,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает независимые порты, собранные на одной сессии и tenant-схеме."""
        (
            self._documents,
            self._warehouses,
            self._items,
            self._locations,
            self._serials,
            self._lots,
        ) = (documents, warehouses, items, locations, serials, lots)
        (
            self._positions,
            self._executions,
            self._postings,
            self._requests,
            self._currencies,
        ) = (positions, executions, postings, requests, currencies)
        self._reader, self._outbox, self._clock, self._uuid = (
            reader,
            outbox,
            clock,
            uuid,
        )

    async def execute(self, command: PostReceiptCommand) -> PostReceiptResultDTO:
        """Фиксирует полную приёмку либо оставляет БД без факта, нулевых позиций и события."""
        claim = await self._requests.claim(
            command.idempotency_key,
            receipt_posting_fingerprint(command),
            command.actor_id,
            self._clock.now(),
        )
        if claim.fingerprint != receipt_posting_fingerprint(command):
            raise ReceiptPostingConflictError(
                "Ключ приёмки уже использован для другого состава."
            )
        if not claim.is_new:
            if claim.result is None:
                raise RuntimeError("Завершённая команда не содержит результата.")
            return claim.result
        document = await self._documents.get_for_update(
            StockDocumentIdVO(command.document_id)
        )
        if document is None:
            raise StockDocumentNotFoundError("Документ поступления не найден.")
        document.ensure_version(command.expected_version)
        document.ensure_manual_receipt()
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
        locations = {}
        location_codes: dict[UUID, str] = {}
        for identifier in sorted({value.location_id for value in command.lines}):
            location = await self._locations.get_for_update(
                StockLocationIdVO(identifier), warehouse_id=document.warehouse_id
            )
            if location is None:
                raise StockLocationNotFoundError(
                    "Локация не найдена в складе документа."
                )
            locations[location.id] = location.snapshot()
            location_codes[location.id.uuid] = location.code.value
        serials = {}
        serial_numbers: dict[UUID, str] = {}
        for identifier in sorted(
            {value.serial_id for value in command.lines if value.serial_id is not None}
        ):
            value = next(
                value for value in command.lines if value.serial_id == identifier
            )
            serial = await self._serials.get_for_update(
                StockSerialIdVO(identifier),
                inventory_item_id=planned[value.client_line_id].inventory_item_id,
            )
            if serial is None:
                raise StockSerialNotFoundError("Экземпляр не найден в SKU строки.")
            serials[serial.id] = serial.snapshot()
            serial_numbers[serial.id.uuid] = serial.number.value
        lots = {}
        lot_numbers: dict[UUID, str] = {}
        for identifier in sorted(
            {value.lot_id for value in command.lines if value.lot_id is not None}
        ):
            value = next(value for value in command.lines if value.lot_id == identifier)
            lot = await self._lots.get_for_update(
                StockLotIdVO(identifier),
                inventory_item_id=planned[value.client_line_id].inventory_item_id,
            )
            if lot is None:
                raise StockLotNotFoundError("Партия не найдена в SKU строки.")
            lots[lot.id] = lot.snapshot()
            lot_numbers[lot.id.uuid] = lot.number.value
        await self._currencies.ensure_codes(
            tuple(sorted({CurrencyVO(cost.currency).value for cost in command.costs}))
        )
        lines = []
        for value in command.lines:
            item = items[planned[value.client_line_id].inventory_item_id]
            dims = StockDimensionsVO(
                item.id,
                StockLocationIdVO(value.location_id),
                document.owner_id,
                StockLotIdVO(value.lot_id) if value.lot_id else None,
                StockSerialIdVO(value.serial_id) if value.serial_id else None,
                value.stock_status,
            )
            lines.append(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(self._uuid.new()),
                    document_line_id=planned[value.client_line_id].id,
                    inventory_item=item.execution_snapshot(),
                    quantity=QuantityVO(value.quantity),
                    uom=UomCodeVO(value.uom),
                    route=ReceiptExecutionRouteVO(dims),
                )
            )
        by_client = {
            value.client_line_id: line.id
            for value, line in zip(command.lines, lines, strict=True)
        }
        costs = tuple(
            ReceiptCostEvidence.create(
                identifier=ReceiptCostEvidenceIdVO(self._uuid.new()),
                total=MoneyVO(cost.amount, CurrencyVO(cost.currency)),
                basis_kind=cost.basis_kind,
                source_system=cost.source_system,
                source_reference=cost.source_reference,
                allocations=tuple(
                    ReceiptCostAllocationVO(
                        by_client[a.client_line_id],
                        MoneyVO(a.amount, CurrencyVO(cost.currency)),
                    )
                    for a in cost.allocations
                ),
            )
            for cost in command.costs
        )
        presence = await self._positions.serial_presence(
            tuple(serial.id for serial in serials.values())
        )
        dimensions = {line.route.dimensions[0] for line in lines}
        positions = []
        for dims in sorted(
            dimensions,
            key=lambda d: (
                d.inventory_item_id.uuid.int,
                d.location_id.uuid.int,
                d.owner_id.uuid.int,
                d.lot_id.uuid.int if d.lot_id else -1,
                d.serial_id.uuid.int if d.serial_id else -1,
                d.stock_status.value,
            ),
        ):
            zero = StockPosition.create(
                identifier=StockPositionIdVO(self._uuid.new()),
                dimensions=dims,
                inventory_item=items[dims.inventory_item_id].stock_snapshot(),
                location=locations[dims.location_id],
                warehouse=warehouse.snapshot(),
                lot=lots.get(dims.lot_id),
                serial=serials.get(dims.serial_id),
            )
            positions.append(await self._positions.get_or_add_for_update(zero))
        bundle = ReceiptPostingService.post(
            document=document,
            expected_version=command.expected_version,
            execution_id=StockExecutionIdVO(self._uuid.new()),
            posting_id=StockPostingIdVO(self._uuid.new()),
            event_id=StockReceiptEventIdVO(self._uuid.new()),
            lines=tuple(lines),
            positions=tuple(positions),
            warehouse=warehouse.snapshot(),
            inventory_items=tuple(item.execution_snapshot() for item in items.values()),
            locations=tuple(locations.values()),
            lots=tuple(lots.values()),
            serials=tuple(serials.values()),
            presence=presence,
            entry_bindings=tuple(
                StockPostingEntryBindingVO(
                    position.id, StockLedgerEntryIdVO(self._uuid.new())
                )
                for position in positions
            ),
            costs=costs,
            now=self._clock.now(),
        )
        await self._executions.add(bundle.execution)
        await self._postings.add(bundle.posting)
        for before, after in zip(bundle.before, bundle.after, strict=True):
            await self._positions.save(after, expected_version=before.version)
        await self._documents.save(
            bundle.document, expected_version=command.expected_version
        )
        header = await self._reader.get(GetReceiptDocumentQuery(document.id.uuid))
        result = receipt_result(
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
                event_type="inventory.stock_receipt_posted",
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
