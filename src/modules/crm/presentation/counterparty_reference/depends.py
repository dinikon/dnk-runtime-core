from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.crm.application.counterparty_reference.port import (
    CounterpartyReferenceRepositoryProtocol,
)
from src.modules.crm.infrastructure.counterparty_reference.repository import (
    SqlAlchemyCounterpartyReferenceRepository,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.handler import (
    SearchCounterpartyReferencesHandler,
)


def get_counterparty_reference_repository(
    uow: UoWDep,
) -> CounterpartyReferenceRepositoryProtocol:
    """Собирает read-порт ссылок на общей tenant-сессии."""
    return SqlAlchemyCounterpartyReferenceRepository(uow.session)


CounterpartyReferenceRepositoryDep = Annotated[
    CounterpartyReferenceRepositoryProtocol,
    Depends(get_counterparty_reference_repository),
]


def get_search_counterparty_references_handler(
    repository: CounterpartyReferenceRepositoryDep,
) -> SearchCounterpartyReferencesHandler:
    """Собирает серверный выбор контрагентов."""
    return SearchCounterpartyReferencesHandler(repository)


SearchCounterpartyReferencesHandlerDep = Annotated[
    SearchCounterpartyReferencesHandler,
    Depends(get_search_counterparty_references_handler),
]
