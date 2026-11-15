from src.modules.inventory.application.stock_document.query.list_issue_sources.handler import (
    ListIssueSourcesHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.issue_query_repository import (
    SqlAlchemyIssueDocumentQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.issue_creation_requests import (
    SqlAlchemyIssueCreationRequests,
)
from src.modules.inventory.application.stock_document.issue_read_service import (
    IssueDocumentReadService,
)
from src.modules.inventory.application.stock_document.command.create_issue_draft.handler import (
    CreateIssueDraftHandler,
)
from src.modules.inventory.application.stock_document.query.get_issue_document.handler import (
    GetIssueDocumentHandler,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.handler import (
    ListIssueDocumentsHandler,
)
from src.modules.inventory.application.stock_document.command.update_issue_document_lines.handler import (
    UpdateIssueDocumentLinesHandler,
)
from src.modules.inventory.application.stock_document.command.confirm_issue_document.handler import (
    ConfirmIssueDocumentHandler,
)
from src.modules.inventory.application.stock_document.command.cancel_issue_document.handler import (
    CancelIssueDocumentHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.issue_requests import (
    SqlAlchemyIssuePostingRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.issue_facts_repository import (
    SqlAlchemyIssueFactsQueryRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.inventory.application.stock_document.command.post_issue.handler import (
    PostIssueHandler,
)
from src.modules.inventory.application.stock_document.query.prepare_issue.handler import (
    PrepareIssueHandler,
)
from src.modules.inventory.application.stock_document.query.list_issue_executions.handler import (
    ListIssueExecutionsHandler,
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


def get_issue_reader(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> IssueDocumentReadService:
    """Собирает собственные проекции и пакетные имена CRM."""
    return IssueDocumentReadService(
        SqlAlchemyIssueDocumentQueryRepository(uow.session), owners
    )


IssueReaderDep = Annotated[IssueDocumentReadService, Depends(get_issue_reader)]


def get_create_issue_handler(
    uow: UoWDep,
    owners: StockOwnerReferenceDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    reader: IssueReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateIssueDraftHandler:
    """Все write/read-порты получают одну сессию внешнего UoW."""
    return CreateIssueDraftHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        SqlAlchemyIssueCreationRequests(uow.session),
        owners,
        warehouses,
        items,
        reader,
        clock,
        uuid,
    )


CreateIssueDraftHandlerDep = Annotated[
    CreateIssueDraftHandler, Depends(get_create_issue_handler)
]


def get_get_issue_handler(reader: IssueReaderDep) -> GetIssueDocumentHandler:
    """Собирает чтение отдельного расхода."""
    return GetIssueDocumentHandler(reader)


GetIssueDocumentHandlerDep = Annotated[
    GetIssueDocumentHandler, Depends(get_get_issue_handler)
]


def get_list_issues_handler(reader: IssueReaderDep) -> ListIssueDocumentsHandler:
    """Собирает список расходов."""
    return ListIssueDocumentsHandler(reader)


ListIssueDocumentsHandlerDep = Annotated[
    ListIssueDocumentsHandler, Depends(get_list_issues_handler)
]


def get_update_issue_document_lines_handler(
    uow: UoWDep,
    reader: IssueReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    uuid: UuidDep,
) -> UpdateIssueDocumentLinesHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return UpdateIssueDocumentLinesHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, uuid
    )


UpdateIssueDocumentLinesHandlerDep = Annotated[
    UpdateIssueDocumentLinesHandler,
    Depends(get_update_issue_document_lines_handler),
]


def get_confirm_issue_document_handler(
    uow: UoWDep,
    reader: IssueReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    warehouses: WarehouseRepositoryDep,
) -> ConfirmIssueDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return ConfirmIssueDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, warehouses
    )


ConfirmIssueDocumentHandlerDep = Annotated[
    ConfirmIssueDocumentHandler, Depends(get_confirm_issue_document_handler)
]


def get_cancel_issue_document_handler(
    uow: UoWDep, reader: IssueReaderDep, clock: ClockDep
) -> CancelIssueDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return CancelIssueDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock
    )


CancelIssueDocumentHandlerDep = Annotated[
    CancelIssueDocumentHandler, Depends(get_cancel_issue_document_handler)
]


def get_post_issue_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    reader: IssueReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PostIssueHandler:
    """Собирает расход, позиции и Outbox на одной сессии внешнего UoW."""
    return PostIssueHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        SqlAlchemyStockExecutionRepository(uow.session),
        SqlAlchemyStockPostingRepository(uow.session),
        SqlAlchemyIssuePostingRequests(uow.session),
        reader,
        SqlAlchemyOutboxRepository(uow.session),
        clock,
        uuid,
    )


PostIssueHandlerDep = Annotated[PostIssueHandler, Depends(get_post_issue_handler)]


def get_prepare_issue_handler(uow: UoWDep) -> PrepareIssueHandler:
    """Собирает согласованную проекцию подготовки расхода."""
    return PrepareIssueHandler(SqlAlchemyIssueFactsQueryRepository(uow.session))


PrepareIssueHandlerDep = Annotated[
    PrepareIssueHandler, Depends(get_prepare_issue_handler)
]


def get_list_issue_executions_handler(uow: UoWDep) -> ListIssueExecutionsHandler:
    """Собирает постраничную историю исполнений расхода."""
    return ListIssueExecutionsHandler(SqlAlchemyIssueFactsQueryRepository(uow.session))


ListIssueExecutionsHandlerDep = Annotated[
    ListIssueExecutionsHandler, Depends(get_list_issue_executions_handler)
]


def get_list_issue_sources_handler(uow: UoWDep) -> ListIssueSourcesHandler:
    """Собирает серверный выбор существующих физических позиций."""
    return ListIssueSourcesHandler(SqlAlchemyIssueFactsQueryRepository(uow.session))


ListIssueSourcesHandlerDep = Annotated[
    ListIssueSourcesHandler, Depends(get_list_issue_sources_handler)
]
