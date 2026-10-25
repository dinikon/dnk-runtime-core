from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.deal.aggregate import Deal


class DealRepositoryProtocol(Protocol):
    """Хранение агрегата Deal в общей транзакции tenant."""

    async def get_for_update(self, record_id: EntityIdVO) -> Deal | None:
        """Загружает агрегат для изменения с блокировкой."""
        ...

    async def add(self, entity: Deal) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: Deal) -> None:
        """Сохраняет агрегат без commit."""
        ...
