from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.crm.application.counterparty_reference.service import (
    CounterpartyReferenceService,
)
from src.modules.crm.infrastructure.counterparty_reference.repository import (
    SqlAlchemyCounterpartyReferenceRepository,
)
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_reference import (
    SupplierReferencePort,
)
from src.modules.supplier_sourcing.application.supplier_source.port.query_repository import (
    SupplierSourceQueryRepositoryProtocol,
)
from src.modules.supplier_sourcing.domain.supplier_source.repository import (
    SupplierSourceRepositoryProtocol,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.crm.supplier_reference import (
    CrmSupplierReferenceAdapter,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.persistence.repository import (
    SqlAlchemySupplierSourceRepository,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.persistence.query_repository import (
    SqlAlchemySupplierSourceQueryRepository,
)
from src.modules.supplier_sourcing.application.supplier_source.command.create_supplier_source.handler import (
    CreateSupplierSourceHandler,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.handler import (
    UpdateSupplierSourceHandler,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.handler import (
    GetSupplierSourceHandler,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.handler import (
    ListSupplierSourcesHandler,
)


def get_supplier_reference(uow: UoWDep) -> SupplierReferencePort:
    """Собирает адаптер публичного контракта CRM на общей сессии."""
    return CrmSupplierReferenceAdapter(
        CounterpartyReferenceService(
            SqlAlchemyCounterpartyReferenceRepository(uow.session)
        )
    )


SupplierReferenceDep = Annotated[SupplierReferencePort, Depends(get_supplier_reference)]


def get_source_repository(uow: UoWDep) -> SupplierSourceRepositoryProtocol:
    """Собирает write-порт агрегата на сессии текущего tenant."""
    return SqlAlchemySupplierSourceRepository(uow.session)


SourceRepositoryDep = Annotated[
    SupplierSourceRepositoryProtocol, Depends(get_source_repository)
]


def get_source_query_repository(uow: UoWDep) -> SupplierSourceQueryRepositoryProtocol:
    """Собирает собственные проекции на той же сессии UoW."""
    return SqlAlchemySupplierSourceQueryRepository(uow.session)


SourceQueryRepositoryDep = Annotated[
    SupplierSourceQueryRepositoryProtocol, Depends(get_source_query_repository)
]


def get_create_source_handler(
    repository: SourceRepositoryDep,
    suppliers: SupplierReferenceDep,
    uuid_generator: UuidDep,
) -> CreateSupplierSourceHandler:
    """Собирает создание без передачи UoW в Application."""
    return CreateSupplierSourceHandler(repository, suppliers, uuid_generator)


CreateSupplierSourceHandlerDep = Annotated[
    CreateSupplierSourceHandler, Depends(get_create_source_handler)
]


def get_update_source_handler(
    repository: SourceRepositoryDep, suppliers: SupplierReferenceDep
) -> UpdateSupplierSourceHandler:
    """Собирает редактирование на портах внешней транзакции."""
    return UpdateSupplierSourceHandler(repository, suppliers)


UpdateSupplierSourceHandlerDep = Annotated[
    UpdateSupplierSourceHandler, Depends(get_update_source_handler)
]


def get_get_source_handler(
    repository: SourceQueryRepositoryDep, suppliers: SupplierReferenceDep
) -> GetSupplierSourceHandler:
    """Собирает чтение карточки и имени поставщика."""
    return GetSupplierSourceHandler(repository, suppliers)


GetSupplierSourceHandlerDep = Annotated[
    GetSupplierSourceHandler, Depends(get_get_source_handler)
]


def get_list_sources_handler(
    repository: SourceQueryRepositoryDep, suppliers: SupplierReferenceDep
) -> ListSupplierSourcesHandler:
    """Собирает страницу источников с пакетным чтением CRM."""
    return ListSupplierSourcesHandler(repository, suppliers)


ListSupplierSourcesHandlerDep = Annotated[
    ListSupplierSourcesHandler, Depends(get_list_sources_handler)
]
