from src.modules.inventory.application.stock_document.query.list_status_change_sources.handler import (
    ListStatusChangeSourcesHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.status_change_query_repository import (
    SqlAlchemyStatusChangeDocumentQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.status_change_creation_requests import (
    SqlAlchemyStatusChangeCreationRequests,
)
from src.modules.inventory.application.stock_document.status_change_read_service import (
    StatusChangeDocumentReadService,
)
from src.modules.inventory.application.stock_document.command.create_status_change_draft.handler import (
    CreateStatusChangeDraftHandler,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.handler import (
    GetStatusChangeDocumentHandler,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.handler import (
    ListStatusChangeDocumentsHandler,
)
from src.modules.inventory.application.stock_document.command.update_status_change_document_lines.handler import (
    UpdateStatusChangeDocumentLinesHandler,
)
from src.modules.inventory.application.stock_document.command.confirm_status_change_document.handler import (
    ConfirmStatusChangeDocumentHandler,
)
from src.modules.inventory.application.stock_document.command.cancel_status_change_document.handler import (
    CancelStatusChangeDocumentHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.status_change_requests import (
    SqlAlchemyStatusChangePostingRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.status_change_facts_repository import (
    SqlAlchemyStatusChangeFactsQueryRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.inventory.application.stock_document.command.post_status_change.handler import (
    PostStatusChangeHandler,
)
from src.modules.inventory.application.stock_document.query.prepare_status_change.handler import (
    PrepareStatusChangeHandler,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.handler import (
    ListStatusChangeExecutionsHandler,
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


def get_status_change_reader(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> StatusChangeDocumentReadService:
    """Собирает собственные проекции и пакетные имена CRM."""
    return StatusChangeDocumentReadService(
        SqlAlchemyStatusChangeDocumentQueryRepository(uow.session), owners
    )


StatusChangeReaderDep = Annotated[
    StatusChangeDocumentReadService, Depends(get_status_change_reader)
]


def get_create_status_change_handler(
    uow: UoWDep,
    owners: StockOwnerReferenceDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    reader: StatusChangeReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateStatusChangeDraftHandler:
    """Все write/read-порты получают одну сессию внешнего UoW."""
    return CreateStatusChangeDraftHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        SqlAlchemyStatusChangeCreationRequests(uow.session),
        owners,
        warehouses,
        items,
        reader,
        clock,
        uuid,
    )


CreateStatusChangeDraftHandlerDep = Annotated[
    CreateStatusChangeDraftHandler, Depends(get_create_status_change_handler)
]


def get_get_status_change_handler(
    reader: StatusChangeReaderDep,
) -> GetStatusChangeDocumentHandler:
    """Собирает чтение отдельного изменения состояния."""
    return GetStatusChangeDocumentHandler(reader)


GetStatusChangeDocumentHandlerDep = Annotated[
    GetStatusChangeDocumentHandler, Depends(get_get_status_change_handler)
]


def get_list_status_changes_handler(
    reader: StatusChangeReaderDep,
) -> ListStatusChangeDocumentsHandler:
    """Собирает список изменений состояния."""
    return ListStatusChangeDocumentsHandler(reader)


ListStatusChangeDocumentsHandlerDep = Annotated[
    ListStatusChangeDocumentsHandler, Depends(get_list_status_changes_handler)
]


def get_update_status_change_document_lines_handler(
    uow: UoWDep,
    reader: StatusChangeReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    uuid: UuidDep,
) -> UpdateStatusChangeDocumentLinesHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return UpdateStatusChangeDocumentLinesHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, uuid
    )


UpdateStatusChangeDocumentLinesHandlerDep = Annotated[
    UpdateStatusChangeDocumentLinesHandler,
    Depends(get_update_status_change_document_lines_handler),
]


def get_confirm_status_change_document_handler(
    uow: UoWDep,
    reader: StatusChangeReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    warehouses: WarehouseRepositoryDep,
) -> ConfirmStatusChangeDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return ConfirmStatusChangeDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, warehouses
    )


ConfirmStatusChangeDocumentHandlerDep = Annotated[
    ConfirmStatusChangeDocumentHandler,
    Depends(get_confirm_status_change_document_handler),
]


def get_cancel_status_change_document_handler(
    uow: UoWDep, reader: StatusChangeReaderDep, clock: ClockDep
) -> CancelStatusChangeDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return CancelStatusChangeDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock
    )


CancelStatusChangeDocumentHandlerDep = Annotated[
    CancelStatusChangeDocumentHandler,
    Depends(get_cancel_status_change_document_handler),
]


def get_post_status_change_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    reader: StatusChangeReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PostStatusChangeHandler:
    """Собирает изменение состояния, позиции и Outbox на одной сессии внешнего UoW."""
    return PostStatusChangeHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        SqlAlchemyStockExecutionRepository(uow.session),
        SqlAlchemyStockPostingRepository(uow.session),
        SqlAlchemyStatusChangePostingRequests(uow.session),
        reader,
        SqlAlchemyOutboxRepository(uow.session),
        clock,
        uuid,
    )


PostStatusChangeHandlerDep = Annotated[
    PostStatusChangeHandler, Depends(get_post_status_change_handler)
]


def get_prepare_status_change_handler(uow: UoWDep) -> PrepareStatusChangeHandler:
    """Собирает согласованную проекцию подготовки изменения состояния."""
    return PrepareStatusChangeHandler(
        SqlAlchemyStatusChangeFactsQueryRepository(uow.session)
    )


PrepareStatusChangeHandlerDep = Annotated[
    PrepareStatusChangeHandler, Depends(get_prepare_status_change_handler)
]


def get_list_status_change_executions_handler(
    uow: UoWDep,
) -> ListStatusChangeExecutionsHandler:
    """Собирает постраничную историю исполнений изменения состояния."""
    return ListStatusChangeExecutionsHandler(
        SqlAlchemyStatusChangeFactsQueryRepository(uow.session)
    )


ListStatusChangeExecutionsHandlerDep = Annotated[
    ListStatusChangeExecutionsHandler,
    Depends(get_list_status_change_executions_handler),
]


def get_list_status_change_sources_handler(
    uow: UoWDep,
) -> ListStatusChangeSourcesHandler:
    """Собирает серверный выбор существующих физических позиций."""
    return ListStatusChangeSourcesHandler(
        SqlAlchemyStatusChangeFactsQueryRepository(uow.session)
    )


ListStatusChangeSourcesHandlerDep = Annotated[
    ListStatusChangeSourcesHandler, Depends(get_list_status_change_sources_handler)
]

from src.modules.inventory.application.stock_document.status_change_context import (
    StatusChangeContextLoader,
)
from src.modules.inventory.application.stock_document.query.preview_status_change.handler import (
    PreviewStatusChangeHandler,
)
from src.modules.inventory.application.stock_document.query.get_status_transitions.handler import (
    GetStatusTransitionsHandler,
)


def get_preview_status_change_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PreviewStatusChangeHandler:
    """Собирает read-only подготовку на той же tenant-сессии без фиксации фактов."""
    loader = StatusChangeContextLoader(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        uuid,
    )
    return PreviewStatusChangeHandler(loader, clock, uuid)


PreviewStatusChangeHandlerDep = Annotated[
    PreviewStatusChangeHandler, Depends(get_preview_status_change_handler)
]


def get_status_transitions_handler() -> GetStatusTransitionsHandler:
    """Собирает чистое чтение Domain-матрицы без инфраструктурных портов."""
    return GetStatusTransitionsHandler()


GetStatusTransitionsHandlerDep = Annotated[
    GetStatusTransitionsHandler, Depends(get_status_transitions_handler)
]
