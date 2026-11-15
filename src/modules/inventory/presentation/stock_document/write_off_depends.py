from src.modules.inventory.application.stock_document.query.list_write_off_sources.handler import (
    ListWriteOffSourcesHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.write_off_query_repository import (
    SqlAlchemyWriteOffDocumentQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.write_off_creation_requests import (
    SqlAlchemyWriteOffCreationRequests,
)
from src.modules.inventory.application.stock_document.write_off_read_service import (
    WriteOffDocumentReadService,
)
from src.modules.inventory.application.stock_document.command.create_write_off_draft.handler import (
    CreateWriteOffDraftHandler,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.handler import (
    GetWriteOffDocumentHandler,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.handler import (
    ListWriteOffDocumentsHandler,
)
from src.modules.inventory.application.stock_document.command.update_write_off_document_lines.handler import (
    UpdateWriteOffDocumentLinesHandler,
)
from src.modules.inventory.application.stock_document.command.confirm_write_off_document.handler import (
    ConfirmWriteOffDocumentHandler,
)
from src.modules.inventory.application.stock_document.command.cancel_write_off_document.handler import (
    CancelWriteOffDocumentHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.write_off_requests import (
    SqlAlchemyWriteOffPostingRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.write_off_facts_repository import (
    SqlAlchemyWriteOffFactsQueryRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.inventory.application.stock_document.command.post_write_off.handler import (
    PostWriteOffHandler,
)
from src.modules.inventory.application.stock_document.query.prepare_write_off.handler import (
    PrepareWriteOffHandler,
)
from src.modules.inventory.application.stock_document.query.list_write_off_executions.handler import (
    ListWriteOffExecutionsHandler,
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


def get_write_off_reader(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> WriteOffDocumentReadService:
    """Собирает собственные проекции и пакетные имена CRM."""
    return WriteOffDocumentReadService(
        SqlAlchemyWriteOffDocumentQueryRepository(uow.session), owners
    )


WriteOffReaderDep = Annotated[
    WriteOffDocumentReadService, Depends(get_write_off_reader)
]


def get_create_write_off_handler(
    uow: UoWDep,
    owners: StockOwnerReferenceDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    reader: WriteOffReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateWriteOffDraftHandler:
    """Все write/read-порты получают одну сессию внешнего UoW."""
    return CreateWriteOffDraftHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        SqlAlchemyWriteOffCreationRequests(uow.session),
        owners,
        warehouses,
        items,
        reader,
        clock,
        uuid,
    )


CreateWriteOffDraftHandlerDep = Annotated[
    CreateWriteOffDraftHandler, Depends(get_create_write_off_handler)
]


def get_get_write_off_handler(reader: WriteOffReaderDep) -> GetWriteOffDocumentHandler:
    """Собирает чтение отдельного списания."""
    return GetWriteOffDocumentHandler(reader)


GetWriteOffDocumentHandlerDep = Annotated[
    GetWriteOffDocumentHandler, Depends(get_get_write_off_handler)
]


def get_list_write_offs_handler(
    reader: WriteOffReaderDep,
) -> ListWriteOffDocumentsHandler:
    """Собирает список списаний."""
    return ListWriteOffDocumentsHandler(reader)


ListWriteOffDocumentsHandlerDep = Annotated[
    ListWriteOffDocumentsHandler, Depends(get_list_write_offs_handler)
]


def get_update_write_off_document_lines_handler(
    uow: UoWDep,
    reader: WriteOffReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    uuid: UuidDep,
) -> UpdateWriteOffDocumentLinesHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return UpdateWriteOffDocumentLinesHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, uuid
    )


UpdateWriteOffDocumentLinesHandlerDep = Annotated[
    UpdateWriteOffDocumentLinesHandler,
    Depends(get_update_write_off_document_lines_handler),
]


def get_confirm_write_off_document_handler(
    uow: UoWDep,
    reader: WriteOffReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    warehouses: WarehouseRepositoryDep,
) -> ConfirmWriteOffDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return ConfirmWriteOffDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, warehouses
    )


ConfirmWriteOffDocumentHandlerDep = Annotated[
    ConfirmWriteOffDocumentHandler, Depends(get_confirm_write_off_document_handler)
]


def get_cancel_write_off_document_handler(
    uow: UoWDep, reader: WriteOffReaderDep, clock: ClockDep
) -> CancelWriteOffDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return CancelWriteOffDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock
    )


CancelWriteOffDocumentHandlerDep = Annotated[
    CancelWriteOffDocumentHandler, Depends(get_cancel_write_off_document_handler)
]


def get_post_write_off_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    reader: WriteOffReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PostWriteOffHandler:
    """Собирает списание, позиции и Outbox на одной сессии внешнего UoW."""
    return PostWriteOffHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        SqlAlchemyStockExecutionRepository(uow.session),
        SqlAlchemyStockPostingRepository(uow.session),
        SqlAlchemyWriteOffPostingRequests(uow.session),
        reader,
        SqlAlchemyOutboxRepository(uow.session),
        clock,
        uuid,
    )


PostWriteOffHandlerDep = Annotated[
    PostWriteOffHandler, Depends(get_post_write_off_handler)
]


def get_prepare_write_off_handler(uow: UoWDep) -> PrepareWriteOffHandler:
    """Собирает согласованную проекцию подготовки списания."""
    return PrepareWriteOffHandler(SqlAlchemyWriteOffFactsQueryRepository(uow.session))


PrepareWriteOffHandlerDep = Annotated[
    PrepareWriteOffHandler, Depends(get_prepare_write_off_handler)
]


def get_list_write_off_executions_handler(uow: UoWDep) -> ListWriteOffExecutionsHandler:
    """Собирает постраничную историю исполнений списания."""
    return ListWriteOffExecutionsHandler(
        SqlAlchemyWriteOffFactsQueryRepository(uow.session)
    )


ListWriteOffExecutionsHandlerDep = Annotated[
    ListWriteOffExecutionsHandler, Depends(get_list_write_off_executions_handler)
]


def get_list_write_off_sources_handler(uow: UoWDep) -> ListWriteOffSourcesHandler:
    """Собирает серверный выбор существующих физических позиций."""
    return ListWriteOffSourcesHandler(
        SqlAlchemyWriteOffFactsQueryRepository(uow.session)
    )


ListWriteOffSourcesHandlerDep = Annotated[
    ListWriteOffSourcesHandler, Depends(get_list_write_off_sources_handler)
]
