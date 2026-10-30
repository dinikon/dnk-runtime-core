from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Protocol
from src.modules.channels.domain.catalog_binding.aggregate import CatalogBindingGroup


class CatalogBindingRepository(Protocol):
    """Хранит только корень группы в общем внешнем UoW."""

    async def get(
        self,
        connection_id: EntityIdVO,
        group_id: EntityIdVO,
        *,
        for_update: bool = False,
    ) -> CatalogBindingGroup | None:
        """Восстанавливает группу или сообщает об отсутствии."""
        ...

    async def save(self, group: CatalogBindingGroup) -> None:
        """Сохраняет группу и её пары без собственного commit."""
        ...

    async def delete(self, group: CatalogBindingGroup) -> None:
        """Снимает всю группу, не меняя Catalog или площадку."""
        ...
