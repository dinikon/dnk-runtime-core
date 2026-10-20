from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.aggregate import ContentUpdateRun


class ContentUpdateRepositoryProtocol(Protocol):
    """Хранит корень с позициями и сериализует пересекающиеся исходящие операции."""

    async def lock_scope(self, channel_id: EntityIdVO) -> None:
        """Сериализует подтверждения одного подключения без длительной сетевой блокировки."""
        ...

    async def lock_request(self, identifier: EntityIdVO) -> None:
        """Сериализует одинаковый run ID также между разными каналами."""
        ...

    async def get(self, identifier: EntityIdVO) -> ContentUpdateRun:
        """Загружает корень вместе с позициями под блокировкой."""
        ...

    async def exists(self, identifier: EntityIdVO) -> bool:
        """Проверяет идемпотентное создание подготовки."""
        ...

    async def busy(self, run: ContentUpdateRun) -> bool:
        """Проверяет незавершённые доставки к тем же публикациям."""
        ...

    async def save(self, run: ContentUpdateRun) -> None:
        """Сохраняет корень и позиции без commit."""
        ...
