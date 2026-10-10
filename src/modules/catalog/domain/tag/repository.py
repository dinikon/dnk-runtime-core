from typing import Protocol
from src.modules.catalog.domain.tag.aggregate import Tag
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO


class TagRepositoryProtocol(Protocol):
    """Хранение полного агрегата и проверка ссылок в общем tenant UoW."""

    async def get(self, identifier: TagIdVO) -> Tag:
        """Восстанавливает корень либо сообщает об отсутствии."""
        ...

    async def add(self, entity: Tag) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: Tag) -> None:
        """Сохраняет корень и переводы без commit."""
        ...

    async def delete(self, entity: Tag) -> None:
        """Удаляет проверенный корень без commit."""
        ...

    async def is_used(self, identifier: TagIdVO) -> bool:
        """Проверяет наличие назначений товарам."""
        ...
