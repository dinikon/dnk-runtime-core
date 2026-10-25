from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.basket.aggregate import Basket


class BasketRepositoryProtocol(Protocol):
    """Хранение агрегата Basket в общей транзакции tenant."""

    async def get_owner_for_update(
        self, model_key: str, owner_id: EntityIdVO
    ) -> Basket | None:
        """Загружает агрегат для изменения с блокировкой."""
        ...

    async def add(self, entity: Basket) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: Basket) -> None:
        """Сохраняет агрегат без commit."""
        ...
