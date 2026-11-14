from dataclasses import replace
from src.modules.crm.application.counterparty_reference.port import (
    CounterpartyReferenceRepositoryProtocol,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.query import (
    SearchCounterpartyReferencesQuery,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.dto import (
    SearchCounterpartyReferencesResultDTO,
)


class SearchCounterpartyReferencesHandler:
    """Читает страницу выбора контрагента без восстановления агрегатов."""

    def __init__(self, repository: CounterpartyReferenceRepositoryProtocol) -> None:
        """Принимает порт проекций текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: SearchCounterpartyReferencesQuery
    ) -> SearchCounterpartyReferencesResultDTO:
        """Нормализует только поисковую строку транспортного запроса."""
        return await self._repository.search(
            replace(query, search=(query.search or "").strip() or None)
        )
