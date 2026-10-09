from typing import Protocol
from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)


class ContentBlockRepositoryProtocol(Protocol):
    """Контракт хранения полного агрегата в сессии текущего tenant."""

    async def get(self, identifier: ContentBlockIdVO) -> ContentBlockDefinition:
        """Восстанавливает агрегат либо сообщает об отсутствии."""
        ...

    async def add(self, entity: ContentBlockDefinition) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: ContentBlockDefinition) -> None:
        """Сохраняет доменное состояние без commit."""
        ...

    async def delete(self, entity: ContentBlockDefinition) -> None:
        """Удаляет агрегат после доменных проверок без commit."""
        ...

    async def is_used(self, identifier: ContentBlockIdVO) -> bool:
        """Проверяет ссылки для защищённого доменного изменения."""
        ...
