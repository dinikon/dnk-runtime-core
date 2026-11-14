from typing import Protocol
from uuid import UUID
from src.modules.crm.application.counterparty_reference.dto import (
    CounterpartyModelKey,
    CounterpartyReferenceDTO,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.query import (
    SearchCounterpartyReferencesQuery,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.dto import (
    SearchCounterpartyReferencesResultDTO,
)


class CounterpartyReferenceRepositoryProtocol(Protocol):
    """Читает публичные ссылки CRM в текущем tenant."""

    async def get(
        self, model_key: CounterpartyModelKey, record_id: UUID, *, lock: bool = False
    ) -> CounterpartyReferenceDTO | None:
        """Проверяет точную пару; lock защищает запись от удаления до конца UoW."""
        ...

    async def get_many(
        self, references: tuple[tuple[CounterpartyModelKey, UUID], ...]
    ) -> dict[tuple[CounterpartyModelKey, UUID], CounterpartyReferenceDTO]:
        """Возвращает имена пакетом, сохраняя тип в ключах результата."""
        ...

    async def search(
        self, query: SearchCounterpartyReferencesQuery
    ) -> SearchCounterpartyReferencesResultDTO:
        """Возвращает страницу выбранного типа контрагентов."""
        ...
