from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.lead.aggregate import Lead


class LeadRepositoryProtocol(Protocol):
    """Хранение агрегата Lead в общей транзакции tenant."""

    async def get_for_update(self, record_id: EntityIdVO) -> Lead | None:
        """Загружает агрегат для изменения с блокировкой."""
        ...

    async def add(self, entity: Lead) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: Lead) -> None:
        """Сохраняет агрегат без commit."""
        ...
