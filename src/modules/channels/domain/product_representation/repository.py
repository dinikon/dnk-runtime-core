from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)


class ProductRepresentationRepositoryProtocol(Protocol):
    """Загружает и сохраняет корень с внутренними привязками без commit."""

    async def get(self, identifier: EntityIdVO) -> ProductRepresentation:
        """Блокирует и восстанавливает весь корень."""
        ...

    async def find(
        self, connection_id: EntityIdVO, item_id: EntityIdVO
    ) -> ProductRepresentation | None:
        """Ищет представление пары под блокировкой владельца товара."""
        ...

    async def save(self, representation: ProductRepresentation) -> None:
        """Сохраняет агрегат и историю на общей сессии."""
        ...
