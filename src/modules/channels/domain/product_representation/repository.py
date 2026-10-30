from typing import Protocol

from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductRepresentationRepositoryProtocol(Protocol):
    """Хранит корень представления на общей сессии внешнего UoW."""

    async def get(self, binding_group_id: EntityIdVO) -> ProductRepresentation | None:
        """Восстанавливает и блокирует запись для изменения после блокировки Channel."""
        ...

    async def save(self, representation: ProductRepresentation) -> None:
        """Сохраняет агрегат без самостоятельного commit и скрытого upsert."""
        ...
