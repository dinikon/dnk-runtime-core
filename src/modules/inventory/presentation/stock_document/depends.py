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
from src.modules.inventory.infrastructure.stock_document.persistence.query_repository import (
    SqlAlchemyReceiptDocumentQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.creation_requests import (
    SqlAlchemyReceiptCreationRequests,
)
from src.modules.inventory.application.stock_document.read_service import (
    ReceiptDocumentReadService,
)
from src.modules.inventory.application.stock_document.command.create_receipt_draft.handler import (
    CreateReceiptDraftHandler,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.handler import (
    GetReceiptDocumentHandler,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.handler import (
    ListReceiptDocumentsHandler,
)
from src.modules.inventory.application.stock_document.command.update_receipt_document_lines.handler import (
    UpdateReceiptDocumentLinesHandler,
)
from src.modules.inventory.application.stock_document.command.confirm_receipt_document.handler import (
    ConfirmReceiptDocumentHandler,
)
from src.modules.inventory.application.stock_document.command.cancel_receipt_document.handler import (
    CancelReceiptDocumentHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_requests import (
    SqlAlchemyReceiptPostingRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_query_repository import (
    SqlAlchemyReceiptFactsQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.receipt_currency import (
    ReferenceReceiptCurrencies,
)
from src.modules.reference_data.infrastructure.currency.persistence.validation_catalog_repository import (
    SqlAlchemyCurrencyValidationCatalogQueryRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.inventory.application.stock_document.command.post_receipt.handler import (
    PostReceiptHandler,
)
from src.modules.inventory.application.stock_document.query.prepare_receipt.handler import (
    PrepareReceiptHandler,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.handler import (
    ListReceiptExecutionsHandler,
)
from src.modules.inventory.application.stock_document.query.list_receipt_references.handler import (
    ListReceiptReferencesHandler,
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


def get_receipt_reader(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ReceiptDocumentReadService:
    """Собирает собственные проекции и пакетные имена CRM."""
    return ReceiptDocumentReadService(
        SqlAlchemyReceiptDocumentQueryRepository(uow.session), owners
    )


ReceiptReaderDep = Annotated[ReceiptDocumentReadService, Depends(get_receipt_reader)]


def get_create_receipt_handler(
    uow: UoWDep,
    owners: StockOwnerReferenceDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    reader: ReceiptReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateReceiptDraftHandler:
    """Все write/read-порты получают одну сессию внешнего UoW."""
    return CreateReceiptDraftHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        SqlAlchemyReceiptCreationRequests(uow.session),
        owners,
        warehouses,
        items,
        reader,
        clock,
        uuid,
    )


CreateReceiptDraftHandlerDep = Annotated[
    CreateReceiptDraftHandler, Depends(get_create_receipt_handler)
]


def get_get_receipt_handler(reader: ReceiptReaderDep) -> GetReceiptDocumentHandler:
    """Собирает чтение отдельного поступления."""
    return GetReceiptDocumentHandler(reader)


GetReceiptDocumentHandlerDep = Annotated[
    GetReceiptDocumentHandler, Depends(get_get_receipt_handler)
]


def get_list_receipts_handler(reader: ReceiptReaderDep) -> ListReceiptDocumentsHandler:
    """Собирает список поступлений."""
    return ListReceiptDocumentsHandler(reader)


ListReceiptDocumentsHandlerDep = Annotated[
    ListReceiptDocumentsHandler, Depends(get_list_receipts_handler)
]


def get_update_receipt_document_lines_handler(
    uow: UoWDep,
    reader: ReceiptReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    uuid: UuidDep,
) -> UpdateReceiptDocumentLinesHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return UpdateReceiptDocumentLinesHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, uuid
    )


UpdateReceiptDocumentLinesHandlerDep = Annotated[
    UpdateReceiptDocumentLinesHandler,
    Depends(get_update_receipt_document_lines_handler),
]


def get_confirm_receipt_document_handler(
    uow: UoWDep,
    reader: ReceiptReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    warehouses: WarehouseRepositoryDep,
) -> ConfirmReceiptDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return ConfirmReceiptDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock, items, warehouses
    )


ConfirmReceiptDocumentHandlerDep = Annotated[
    ConfirmReceiptDocumentHandler, Depends(get_confirm_receipt_document_handler)
]


def get_cancel_receipt_document_handler(
    uow: UoWDep, reader: ReceiptReaderDep, clock: ClockDep
) -> CancelReceiptDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return CancelReceiptDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock
    )


CancelReceiptDocumentHandlerDep = Annotated[
    CancelReceiptDocumentHandler, Depends(get_cancel_receipt_document_handler)
]


def get_post_receipt_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    reader: ReceiptReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PostReceiptHandler:
    """Собирает физический учёт и глобальный Outbox на одной сессии внешнего UoW."""
    return PostReceiptHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        SqlAlchemyStockExecutionRepository(uow.session),
        SqlAlchemyStockPostingRepository(uow.session),
        SqlAlchemyReceiptPostingRequests(uow.session),
        ReferenceReceiptCurrencies(
            SqlAlchemyCurrencyValidationCatalogQueryRepository(uow.session)
        ),
        reader,
        SqlAlchemyOutboxRepository(uow.session),
        clock,
        uuid,
    )


PostReceiptHandlerDep = Annotated[PostReceiptHandler, Depends(get_post_receipt_handler)]


def get_prepare_receipt_handler(uow: UoWDep) -> PrepareReceiptHandler:
    """Собирает проекцию подготовки без загрузки Domain."""
    return PrepareReceiptHandler(SqlAlchemyReceiptFactsQueryRepository(uow.session))


PrepareReceiptHandlerDep = Annotated[
    PrepareReceiptHandler, Depends(get_prepare_receipt_handler)
]


def get_list_receipt_executions_handler(uow: UoWDep) -> ListReceiptExecutionsHandler:
    """Собирает пагинацию истории одного документа."""
    return ListReceiptExecutionsHandler(
        SqlAlchemyReceiptFactsQueryRepository(uow.session)
    )


ListReceiptExecutionsHandlerDep = Annotated[
    ListReceiptExecutionsHandler, Depends(get_list_receipt_executions_handler)
]


def get_list_receipt_references_handler(uow: UoWDep) -> ListReceiptReferencesHandler:
    """Собирает серверный поиск по собственным моделям Inventory."""
    return ListReceiptReferencesHandler(
        SqlAlchemyReceiptFactsQueryRepository(uow.session)
    )


ListReceiptReferencesHandlerDep = Annotated[
    ListReceiptReferencesHandler, Depends(get_list_receipt_references_handler)
]
