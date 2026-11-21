from uuid import UUID

from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentCreationConflictError,
    StockDocumentLineCreationError,
    StockDocumentOwnerNotFoundError,
)
from src.modules.inventory.application.stock_document.command.create_internal_move_draft.command import (
    CreateInternalMoveDraftCommand,
)
from src.modules.inventory.application.stock_document.command.create_internal_move_draft.dto import (
    CreateInternalMoveDraftResultDTO,
    CreateInternalMoveDraftLineDTO,
)
from src.modules.inventory.application.stock_document.internal_move_creation_fingerprint import (
    internal_move_creation_fingerprint,
)
from src.modules.inventory.application.stock_document.port.internal_move_creation_requests import (
    InternalMoveCreationRequestsPort,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
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
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateInternalMoveDraftHandler:
    """Создаёт только план перемещения; физическое исполнение не вызывается."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        requests: InternalMoveCreationRequestsPort,
        owners: StockOwnerReferencePort,
        warehouses: WarehouseRepositoryProtocol,
        items: InventoryItemRepositoryProtocol,
        reader: InternalMoveDocumentReadService,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общей транзакции без доступа к SQL-сессии."""
        (
            self._repository,
            self._requests,
            self._owners,
            self._warehouses,
            self._items,
            self._reader,
            self._clock,
            self._uuid,
        ) = (
            repository,
            requests,
            owners,
            warehouses,
            items,
            reader,
            clock,
            uuid_generator,
        )

    async def execute(
        self, command: CreateInternalMoveDraftCommand
    ) -> CreateInternalMoveDraftResultDTO:
        """Фиксирует агрегат и исходный ответ атомарно; повтор не перечитывает текущие справочники."""
        now = self._clock.now()
        fingerprint = internal_move_creation_fingerprint(command)
        claim = await self._requests.claim(
            command.actor_id, command.idempotency_key, fingerprint, now
        )
        if claim.fingerprint != fingerprint:
            raise StockDocumentCreationConflictError(
                "Idempotency-Key уже использован для другого состава документа."
            )
        if not claim.is_new:
            if claim.result is None:
                raise RuntimeError(
                    "Зафиксированный запрос создания не содержит результата."
                )
            return claim.result
        owner = await self._owners.get(command.owner_id, lock=True)
        if owner is None:
            raise StockDocumentOwnerNotFoundError("Компания-владелец не найдена.")
        warehouse = await self._warehouses.get_for_share(
            WarehouseIdVO(command.warehouse_id)
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        document = StockDocument.create(
            identifier=StockDocumentIdVO(self._uuid.new()),
            operation_type=StockOperationType.INTERNAL_MOVE,
            warehouse=warehouse.snapshot(),
            owner_id=StockOwnerIdVO(command.owner_id),
            created_at=now,
        )
        snapshots: dict[UUID, InventoryItemDocumentSnapshot] = {}
        for identifier in sorted({line.inventory_item_id for line in command.lines}):
            item = await self._items.get_for_update(InventoryItemIdVO(identifier))
            if item is None:
                raise InventoryItemNotFoundError("SKU плановой строки не найден.")
            snapshots[identifier] = item.document_snapshot()
        for position, value in enumerate(command.lines):
            try:
                snapshot = snapshots[value.inventory_item_id]
                line = StockDocumentLine.create(
                    identifier=StockDocumentLineIdVO(self._uuid.new()),
                    inventory_item=snapshot,
                    quantity=QuantityVO(value.quantity),
                    uom=UomCodeVO(value.uom),
                )
                document = document.add_line(
                    line, inventory_item=snapshot, updated_at=now
                )
            except DomainError as exc:
                raise StockDocumentLineCreationError(position, str(exc)) from exc
        await self._repository.add(document)
        result = await self._reader.get(GetInternalMoveDocumentQuery(document.id.uuid))
        created = CreateInternalMoveDraftResultDTO(
            id=result.id,
            operation_type=result.operation_type,
            status=result.status,
            warehouse_id=result.warehouse_id,
            warehouse_code=result.warehouse_code,
            warehouse_name=result.warehouse_name,
            owner_id=result.owner_id,
            owner_name=result.owner_name,
            source_system=result.source_system,
            source_reference=result.source_reference,
            source_version=result.source_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            version=result.version,
            lines=tuple(
                CreateInternalMoveDraftLineDTO(
                    id=line.id,
                    position=line.position,
                    inventory_item_id=line.inventory_item_id,
                    sku=line.sku,
                    base_uom=line.base_uom,
                    planned_qty=line.planned_qty,
                    source_quantity=line.source_quantity,
                    source_uom=line.source_uom,
                    factor_to_base=line.factor_to_base,
                    executed_qty=line.executed_qty,
                    remaining_qty=line.remaining_qty,
                )
                for line in result.lines
            ),
        )
        await self._requests.complete(
            command.actor_id, command.idempotency_key, created
        )
        return created
