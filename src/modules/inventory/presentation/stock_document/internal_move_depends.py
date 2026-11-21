from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.handler import (
    ListInternalMoveDestinationsHandler,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.handler import (
    ListInternalMoveSourcesHandler,
)
from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.inventory.presentation.inventory_item.depends import (
    InventoryItemRepositoryDep,
)
from src.modules.inventory.presentation.warehouse.depends import WarehouseRepositoryDep
from src.modules.crm.application.counterparty_reference.service import (
    CounterpartyReferenceService,
)
from src.modules.crm.infrastructure.counterparty_reference.repository import (
    SqlAlchemyCounterpartyReferenceRepository,
)
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReferencePort,
)
from src.modules.inventory.infrastructure.stock_document.owner_reference import (
    CrmStockOwnerReference,
)
from src.modules.inventory.infrastructure.stock_document.persistence.repository import (
    SqlAlchemyStockDocumentRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_query_repository import (
    SqlAlchemyInternalMoveDocumentQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_creation_requests import (
    SqlAlchemyInternalMoveCreationRequests,
)
from src.modules.inventory.application.stock_document.internal_move_read_service import (
    InternalMoveDocumentReadService,
)
from src.modules.inventory.application.stock_document.command.create_internal_move_draft.handler import (
    CreateInternalMoveDraftHandler,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.handler import (
    GetInternalMoveDocumentHandler,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.handler import (
    ListInternalMoveDocumentsHandler,
)
from src.modules.inventory.application.stock_document.command.update_internal_move_document_lines.handler import (
    UpdateInternalMoveDocumentLinesHandler,
)
from src.modules.inventory.application.stock_document.command.confirm_internal_move_document.handler import (
    ConfirmInternalMoveDocumentHandler,
)
from src.modules.inventory.application.stock_document.command.cancel_internal_move_document.handler import (
    CancelInternalMoveDocumentHandler,
)


from src.modules.inventory.presentation.stock_location.depends import (
    StockLocationRepositoryDep,
)
from src.modules.inventory.presentation.stock_serial.depends import (
    StockSerialRepositoryDep,
)
from src.modules.inventory.presentation.stock_lot.depends import StockLotRepositoryDep
from src.modules.inventory.infrastructure.stock_position.persistence.repository import (
    SqlAlchemyStockPositionRepository,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.repository import (
    SqlAlchemyStockExecutionRepository,
)
from src.modules.inventory.infrastructure.stock_posting.persistence.repository import (
    SqlAlchemyStockPostingRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_requests import (
    SqlAlchemyInternalMovePostingRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_facts_repository import (
    SqlAlchemyInternalMoveFactsQueryRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.inventory.application.stock_document.command.post_internal_move.handler import (
    PostInternalMoveHandler,
)
from src.modules.inventory.application.stock_document.query.prepare_internal_move.handler import (
    PrepareInternalMoveHandler,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.handler import (
    ListInternalMoveExecutionsHandler,
)


def get_stock_owner_reference(uow: UoWDep) -> StockOwnerReferencePort:
    """Собирает публичный контракт CRM на общей tenant-сессии."""
    return CrmStockOwnerReference(
        CounterpartyReferenceService(
            SqlAlchemyCounterpartyReferenceRepository(uow.session)
        )
    )


StockOwnerReferenceDep = Annotated[
    StockOwnerReferencePort, Depends(get_stock_owner_reference)
]


def get_internal_move_reader(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> InternalMoveDocumentReadService:
    """Собирает собственные проекции и пакетные имена CRM."""
    return InternalMoveDocumentReadService(
        SqlAlchemyInternalMoveDocumentQueryRepository(uow.session), owners
    )


InternalMoveReaderDep = Annotated[
    InternalMoveDocumentReadService, Depends(get_internal_move_reader)
]


def get_create_internal_move_handler(
    uow: UoWDep,
    owners: StockOwnerReferenceDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    reader: InternalMoveReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateInternalMoveDraftHandler:
    """Все write/read-порты получают одну сессию внешнего UoW."""
    return CreateInternalMoveDraftHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        SqlAlchemyInternalMoveCreationRequests(uow.session),
        owners,
        warehouses,
        items,
        reader,
        clock,
        uuid,
    )


CreateInternalMoveDraftHandlerDep = Annotated[
    CreateInternalMoveDraftHandler, Depends(get_create_internal_move_handler)
]


def get_get_internal_move_handler(
    reader: InternalMoveReaderDep,
) -> GetInternalMoveDocumentHandler:
    """Собирает чтение отдельного перемещения."""
    return GetInternalMoveDocumentHandler(reader)


GetInternalMoveDocumentHandlerDep = Annotated[
    GetInternalMoveDocumentHandler, Depends(get_get_internal_move_handler)
]


def get_list_internal_moves_handler(
    reader: InternalMoveReaderDep,
) -> ListInternalMoveDocumentsHandler:
    """Собирает список перемещений."""
    return ListInternalMoveDocumentsHandler(reader)


ListInternalMoveDocumentsHandlerDep = Annotated[
    ListInternalMoveDocumentsHandler, Depends(get_list_internal_moves_handler)
]


def get_update_internal_move_document_lines_handler(
    uow: UoWDep,
    reader: InternalMoveReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    uuid: UuidDep,
) -> UpdateInternalMoveDocumentLinesHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return UpdateInternalMoveDocumentLinesHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, uuid
    )


UpdateInternalMoveDocumentLinesHandlerDep = Annotated[
    UpdateInternalMoveDocumentLinesHandler,
    Depends(get_update_internal_move_document_lines_handler),
]


def get_confirm_internal_move_document_handler(
    uow: UoWDep,
    reader: InternalMoveReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    warehouses: WarehouseRepositoryDep,
) -> ConfirmInternalMoveDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return ConfirmInternalMoveDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, warehouses
    )


ConfirmInternalMoveDocumentHandlerDep = Annotated[
    ConfirmInternalMoveDocumentHandler,
    Depends(get_confirm_internal_move_document_handler),
]


def get_cancel_internal_move_document_handler(
    uow: UoWDep, reader: InternalMoveReaderDep, clock: ClockDep
) -> CancelInternalMoveDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return CancelInternalMoveDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock
    )


CancelInternalMoveDocumentHandlerDep = Annotated[
    CancelInternalMoveDocumentHandler,
    Depends(get_cancel_internal_move_document_handler),
]


def get_post_internal_move_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    reader: InternalMoveReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PostInternalMoveHandler:
    """Собирает перемещение, позиции и Outbox на одной сессии внешнего UoW."""
    return PostInternalMoveHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        SqlAlchemyStockExecutionRepository(uow.session),
        SqlAlchemyStockPostingRepository(uow.session),
        SqlAlchemyInternalMovePostingRequests(uow.session),
        reader,
        SqlAlchemyOutboxRepository(uow.session),
        clock,
        uuid,
    )


PostInternalMoveHandlerDep = Annotated[
    PostInternalMoveHandler, Depends(get_post_internal_move_handler)
]


def get_prepare_internal_move_handler(uow: UoWDep) -> PrepareInternalMoveHandler:
    """Собирает согласованную проекцию подготовки перемещения."""
    return PrepareInternalMoveHandler(
        SqlAlchemyInternalMoveFactsQueryRepository(uow.session)
    )


PrepareInternalMoveHandlerDep = Annotated[
    PrepareInternalMoveHandler, Depends(get_prepare_internal_move_handler)
]


def get_list_internal_move_executions_handler(
    uow: UoWDep,
) -> ListInternalMoveExecutionsHandler:
    """Собирает постраничную историю исполнений перемещения."""
    return ListInternalMoveExecutionsHandler(
        SqlAlchemyInternalMoveFactsQueryRepository(uow.session)
    )


ListInternalMoveExecutionsHandlerDep = Annotated[
    ListInternalMoveExecutionsHandler,
    Depends(get_list_internal_move_executions_handler),
]


def get_list_internal_move_sources_handler(
    uow: UoWDep,
) -> ListInternalMoveSourcesHandler:
    """Собирает серверный выбор существующих физических позиций."""
    return ListInternalMoveSourcesHandler(
        SqlAlchemyInternalMoveFactsQueryRepository(uow.session)
    )


ListInternalMoveSourcesHandlerDep = Annotated[
    ListInternalMoveSourcesHandler, Depends(get_list_internal_move_sources_handler)
]


def get_list_internal_move_destinations_handler(
    uow: UoWDep,
) -> ListInternalMoveDestinationsHandler:
    """Собирает чтение допустимых адресов на tenant-сессии внешнего UoW."""
    return ListInternalMoveDestinationsHandler(
        SqlAlchemyInternalMoveFactsQueryRepository(uow.session)
    )


ListInternalMoveDestinationsHandlerDep = Annotated[
    ListInternalMoveDestinationsHandler,
    Depends(get_list_internal_move_destinations_handler),
]
