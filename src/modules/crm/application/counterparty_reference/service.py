from uuid import UUID
from src.modules.crm.application.counterparty_reference.dto import (
    CounterpartyModelKey,
    CounterpartyReferenceDTO,
)
from src.modules.crm.application.counterparty_reference.port import (
    CounterpartyReferenceRepositoryProtocol,
)


class CounterpartyReferenceService:
    """Публичный контракт проверки и пакетного чтения контрагентов CRM."""

    def __init__(self, repository: CounterpartyReferenceRepositoryProtocol) -> None:
        """Принимает read-порт общего tenant-UoW."""
        self._repository = repository

    async def get(
        self, model_key: CounterpartyModelKey, record_id: UUID, *, lock: bool = False
    ) -> CounterpartyReferenceDTO | None:
        """Получает выбранный тип контрагента без неявного поиска по другим таблицам."""
        return await self._repository.get(model_key, record_id, lock=lock)

    async def get_many(
        self, references: tuple[tuple[CounterpartyModelKey, UUID], ...]
    ) -> dict[tuple[CounterpartyModelKey, UUID], CounterpartyReferenceDTO]:
        """Возвращает имена с ключом из типа и UUID."""
        return await self._repository.get_many(references)
