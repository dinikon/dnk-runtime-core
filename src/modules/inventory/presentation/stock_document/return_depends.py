from src.modules.inventory.application.stock_document.query.list_return_destinations.handler import (
    ListReturnDestinationsHandler,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_origin_repository import (
    SqlAlchemyReturnOriginRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_origin_query_repository import (
    SqlAlchemyReturnOriginQueryRepository,
)
from src.modules.inventory.application.stock_document.query.get_return_origin.handler import (
    GetReturnOriginHandler,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.handler import (
    ListReturnSourcesHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.return_query_repository import (
    SqlAlchemyReturnDocumentQueryRepository,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_creation_requests import (
    SqlAlchemyReturnCreationRequests,
)
from src.modules.inventory.application.stock_document.return_read_service import (
    ReturnDocumentReadService,
)
from src.modules.inventory.application.stock_document.command.create_return_draft.handler import (
    CreateReturnDraftHandler,
)
from src.modules.inventory.application.stock_document.query.get_return_document.handler import (
    GetReturnDocumentHandler,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.handler import (
    ListReturnDocumentsHandler,
)
from src.modules.inventory.application.stock_document.command.update_return_document_lines.handler import (
    UpdateReturnDocumentLinesHandler,
)
from src.modules.inventory.application.stock_document.command.confirm_return_document.handler import (
    ConfirmReturnDocumentHandler,
)
from src.modules.inventory.application.stock_document.command.cancel_return_document.handler import (
    CancelReturnDocumentHandler,
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
from src.modules.inventory.infrastructure.stock_document.persistence.return_requests import (
    SqlAlchemyReturnPostingRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_facts_repository import (
    SqlAlchemyReturnFactsQueryRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.inventory.application.stock_document.command.post_return.handler import (
    PostReturnHandler,
)
from src.modules.inventory.application.stock_document.query.prepare_return.handler import (
    PrepareReturnHandler,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.handler import (
    ListReturnExecutionsHandler,
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


def get_return_reader(
    uow: UoWDep, owners: StockOwnerReferenceDep
) -> ReturnDocumentReadService:
    """Собирает собственные проекции и пакетные имена CRM."""
    return ReturnDocumentReadService(
        SqlAlchemyReturnDocumentQueryRepository(uow.session), owners
    )


ReturnReaderDep = Annotated[ReturnDocumentReadService, Depends(get_return_reader)]


def get_create_return_handler(
    uow: UoWDep,
    owners: StockOwnerReferenceDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    reader: ReturnReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateReturnDraftHandler:
    """Все write/read-порты получают одну сессию внешнего UoW."""
    return CreateReturnDraftHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        SqlAlchemyReturnCreationRequests(uow.session),
        owners,
        warehouses,
        items,
        reader,
        clock,
        uuid,
        SqlAlchemyReturnOriginRepository(uow.session),
    )


CreateReturnDraftHandlerDep = Annotated[
    CreateReturnDraftHandler, Depends(get_create_return_handler)
]


def get_get_return_handler(
    reader: ReturnReaderDep,
) -> GetReturnDocumentHandler:
    """Собирает чтение отдельного возврата."""
    return GetReturnDocumentHandler(reader)


GetReturnDocumentHandlerDep = Annotated[
    GetReturnDocumentHandler, Depends(get_get_return_handler)
]


def get_list_returns_handler(
    reader: ReturnReaderDep,
) -> ListReturnDocumentsHandler:
    """Собирает список изменений состояния."""
    return ListReturnDocumentsHandler(reader)


ListReturnDocumentsHandlerDep = Annotated[
    ListReturnDocumentsHandler, Depends(get_list_returns_handler)
]


def get_update_return_document_lines_handler(
    uow: UoWDep,
    reader: ReturnReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    uuid: UuidDep,
) -> UpdateReturnDocumentLinesHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return UpdateReturnDocumentLinesHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        reader,
        clock,
        items,
        uuid,
        SqlAlchemyReturnOriginRepository(uow.session),
    )


UpdateReturnDocumentLinesHandlerDep = Annotated[
    UpdateReturnDocumentLinesHandler,
    Depends(get_update_return_document_lines_handler),
]


def get_confirm_return_document_handler(
    uow: UoWDep,
    reader: ReturnReaderDep,
    clock: ClockDep,
    items: InventoryItemRepositoryDep,
    warehouses: WarehouseRepositoryDep,
) -> ConfirmReturnDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return ConfirmReturnDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        reader,
        clock,
        items,
        warehouses,
        SqlAlchemyReturnOriginRepository(uow.session),
    )


ConfirmReturnDocumentHandlerDep = Annotated[
    ConfirmReturnDocumentHandler,
    Depends(get_confirm_return_document_handler),
]


def get_cancel_return_document_handler(
    uow: UoWDep, reader: ReturnReaderDep, clock: ClockDep
) -> CancelReturnDocumentHandler:
    """Собирает действие на сессии единственного внешнего tenant-UoW."""
    return CancelReturnDocumentHandler(
        SqlAlchemyStockDocumentRepository(uow.session), reader, clock
    )


CancelReturnDocumentHandlerDep = Annotated[
    CancelReturnDocumentHandler,
    Depends(get_cancel_return_document_handler),
]


def get_post_return_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    reader: ReturnReaderDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PostReturnHandler:
    """Собирает возврат, позиции и Outbox на одной сессии внешнего UoW."""
    return PostReturnHandler(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        SqlAlchemyStockExecutionRepository(uow.session),
        SqlAlchemyStockPostingRepository(uow.session),
        SqlAlchemyReturnPostingRequests(uow.session),
        reader,
        SqlAlchemyOutboxRepository(uow.session),
        clock,
        uuid,
        SqlAlchemyReturnOriginRepository(uow.session),
    )


PostReturnHandlerDep = Annotated[PostReturnHandler, Depends(get_post_return_handler)]


def get_prepare_return_handler(uow: UoWDep) -> PrepareReturnHandler:
    """Собирает согласованную проекцию подготовки возврата."""
    return PrepareReturnHandler(SqlAlchemyReturnFactsQueryRepository(uow.session))


PrepareReturnHandlerDep = Annotated[
    PrepareReturnHandler, Depends(get_prepare_return_handler)
]


def get_list_return_executions_handler(
    uow: UoWDep,
) -> ListReturnExecutionsHandler:
    """Собирает постраничную историю исполнений возврата."""
    return ListReturnExecutionsHandler(
        SqlAlchemyReturnFactsQueryRepository(uow.session)
    )


ListReturnExecutionsHandlerDep = Annotated[
    ListReturnExecutionsHandler,
    Depends(get_list_return_executions_handler),
]


def get_list_return_sources_handler(
    uow: UoWDep,
) -> ListReturnSourcesHandler:
    """Собирает серверный выбор существующих физических позиций."""
    return ListReturnSourcesHandler(SqlAlchemyReturnFactsQueryRepository(uow.session))


ListReturnSourcesHandlerDep = Annotated[
    ListReturnSourcesHandler, Depends(get_list_return_sources_handler)
]

from src.modules.inventory.application.stock_document.return_context import (
    ReturnContextLoader,
)
from src.modules.inventory.application.stock_document.query.preview_return.handler import (
    PreviewReturnHandler,
)


def get_preview_return_handler(
    uow: UoWDep,
    warehouses: WarehouseRepositoryDep,
    items: InventoryItemRepositoryDep,
    locations: StockLocationRepositoryDep,
    serials: StockSerialRepositoryDep,
    lots: StockLotRepositoryDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> PreviewReturnHandler:
    """Собирает read-only подготовку на той же tenant-сессии без фиксации фактов."""
    loader = ReturnContextLoader(
        SqlAlchemyStockDocumentRepository(uow.session),
        warehouses,
        items,
        locations,
        serials,
        lots,
        SqlAlchemyStockPositionRepository(uow.session),
        uuid,
        SqlAlchemyReturnOriginRepository(uow.session),
    )
    return PreviewReturnHandler(loader, clock, uuid)


PreviewReturnHandlerDep = Annotated[
    PreviewReturnHandler, Depends(get_preview_return_handler)
]


def get_return_origin_handler(uow: UoWDep) -> GetReturnOriginHandler:
    """Собирает бизнес-проверку и отдельное чтение контекста по одной tenant-сессии."""
    return GetReturnOriginHandler(
        SqlAlchemyReturnOriginRepository(uow.session),
        SqlAlchemyReturnOriginQueryRepository(uow.session),
    )


GetReturnOriginHandlerDep = Annotated[
    GetReturnOriginHandler, Depends(get_return_origin_handler)
]


def get_list_return_destinations_handler(uow: UoWDep) -> ListReturnDestinationsHandler:
    """Подключает поиск адресов на общей tenant-сессии."""
    return ListReturnDestinationsHandler(
        SqlAlchemyReturnFactsQueryRepository(uow.session)
    )


ListReturnDestinationsHandlerDep = Annotated[
    ListReturnDestinationsHandler, Depends(get_list_return_destinations_handler)
]
