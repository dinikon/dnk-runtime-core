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
