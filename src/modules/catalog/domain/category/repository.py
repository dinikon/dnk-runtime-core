from typing import Protocol
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


class CategoryRepositoryProtocol(Protocol):
    """Хранение полного агрегата и проверка ссылок в общем tenant UoW."""

    async def get(self, identifier: CategoryIdVO) -> Category:
        """Восстанавливает корень либо сообщает об отсутствии."""
        ...

    async def add(self, entity: Category) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: Category) -> None:
        """Сохраняет корень и переводы без commit."""
        ...

    async def delete(self, entity: Category) -> None:
        """Удаляет проверенный корень без commit."""
        ...

    async def is_used(self, identifier: CategoryIdVO) -> bool:
        """Проверяет назначения товарам и наличие дочерних узлов."""
        ...
