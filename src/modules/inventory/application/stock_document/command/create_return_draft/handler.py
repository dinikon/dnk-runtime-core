from src.modules.inventory.application.stock_document.port.return_origin import (
    ReturnOriginPort,
)
from src.modules.inventory.domain.policy.stock_return import StockReturnPolicy
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_details import (
    StockReturnDetailsVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_reason import (
    ReturnReasonVO,
)
from uuid import UUID

from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentNotFoundError,
    StockDocumentCreationConflictError,
    StockDocumentLineCreationError,
    StockDocumentOwnerNotFoundError,
)
from src.modules.inventory.application.stock_document.command.create_return_draft.command import (
    CreateReturnDraftCommand,
)
from src.modules.inventory.application.stock_document.command.create_return_draft.dto import (
    CreateReturnDraftResultDTO,
    CreateReturnDraftLineDTO,
)
from src.modules.inventory.application.stock_document.return_creation_fingerprint import (
    return_creation_fingerprint,
)
from src.modules.inventory.application.stock_document.port.return_creation_requests import (
    ReturnCreationRequestsPort,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
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
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateReturnDraftHandler:
    """Создаёт только план возврата; физическое исполнение не вызывается."""

    def __init__(
        self,
        repository: StockDocumentRepositoryProtocol,
        requests: ReturnCreationRequestsPort,
        owners: StockOwnerReferencePort,
        warehouses: WarehouseRepositoryProtocol,
        items: InventoryItemRepositoryProtocol,
        reader: ReturnDocumentReadService,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
        origin: ReturnOriginPort,
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
        self._origin = origin

    async def execute(
        self, command: CreateReturnDraftCommand
    ) -> CreateReturnDraftResultDTO:
        """Фиксирует агрегат и исходный ответ атомарно; повтор не перечитывает текущие справочники."""
        now = self._clock.now()
        fingerprint = return_creation_fingerprint(command)
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
        origin = await self._origin.get(
            StockExecutionIdVO(command.origin_execution_id), lock=False
        )
        if origin is None:
            raise StockDocumentNotFoundError("Исходное исполнение не найдено.")
        direction = StockReturnPolicy.direction(origin)
        owner = await self._owners.get(origin.owner_id.uuid, lock=True)
        if owner is None:
            raise StockDocumentOwnerNotFoundError("Компания-владелец не найдена.")
        warehouse = await self._warehouses.get_for_share(origin.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        document = StockDocument.create(
            identifier=StockDocumentIdVO(self._uuid.new()),
            operation_type=StockOperationType.RETURN,
            return_details=StockReturnDetailsVO(
                origin.id, direction, ReturnReasonVO(command.reason)
            ),
            warehouse=warehouse.snapshot(),
            owner_id=origin.owner_id,
            created_at=now,
        )
        sources = {
            v.origin_execution_line_id: StockReturnPolicy.line(
                origin, StockExecutionLineIdVO(v.origin_execution_line_id)
            )
            for v in command.lines
        }
        snapshots: dict[UUID, InventoryItemDocumentSnapshot] = {}
        for identifier in sorted(
            {v.dimensions.inventory_item_id.uuid for v in sources.values()}
        ):
            item = await self._items.get_for_update(InventoryItemIdVO(identifier))
            if item is None:
                raise InventoryItemNotFoundError("SKU исходной строки не найден.")
            snapshots[identifier] = item.document_snapshot()
        for index, value in enumerate(command.lines):
            try:
                source = sources[value.origin_execution_line_id]
                snapshot = snapshots[source.dimensions.inventory_item_id.uuid]
                line = StockDocumentLine.create(
                    identifier=StockDocumentLineIdVO(self._uuid.new()),
                    inventory_item=snapshot,
                    quantity=QuantityVO(value.quantity),
                    uom=UomCodeVO(value.uom),
                    return_origin_line_id=source.id,
                )
                document = document.add_line(
                    line, inventory_item=snapshot, updated_at=now
                )
            except DomainError as exc:
                raise StockDocumentLineCreationError(index, str(exc)) from exc
        StockReturnPolicy.ensure_plan(
            details=document.return_snapshot(),
            warehouse_id=document.warehouse_id,
            owner_id=document.owner_id,
            lines=document.lines,
            origin=origin,
            usage=await self._origin.usage(origin.id),
        )
        await self._repository.add(document)
        result = await self._reader.get(GetReturnDocumentQuery(document.id.uuid))
        created = CreateReturnDraftResultDTO(
            id=result.id,
            operation_type=result.operation_type,
            status=result.status,
            warehouse_id=result.warehouse_id,
            warehouse_code=result.warehouse_code,
            warehouse_name=result.warehouse_name,
            owner_id=result.owner_id,
            owner_name=result.owner_name,
            reason=result.reason,
            direction=result.direction,
            origin_execution_id=result.origin_execution_id,
            source_system=result.source_system,
            source_reference=result.source_reference,
            source_version=result.source_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            version=result.version,
            lines=tuple(
                CreateReturnDraftLineDTO(
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
                    origin_execution_line_id=line.origin_execution_line_id,
                )
                for line in result.lines
            ),
        )
        await self._requests.complete(
            command.actor_id, command.idempotency_key, created
        )
        return created
