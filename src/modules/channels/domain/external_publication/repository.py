"""Контракт хранения публикаций, независимых от SyncRun."""

from typing import Protocol

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)


class ExternalPublicationRepositoryProtocol(Protocol):
    """Сохраняет доменные агрегаты на общей транзакции страницы."""

    async def by_keys(
        self, connection_id: EntityIdVO, keys: tuple[tuple[str, str], ...]
    ) -> tuple[ExternalPublication, ...]:
        """Восстанавливает полученные публикации по внешним ключам."""
        ...

    async def affected_tree(
        self, connection_id: EntityIdVO, publication_ids: tuple[EntityIdVO, ...]
    ) -> tuple[ExternalPublication, ...]:
        """Загружает родителей и детей для проверки итоговой структуры."""
        ...

    async def save(self, publication: ExternalPublication) -> None:
        """Сохраняет прошедший Domain-проверки снимок без commit."""
        ...

    async def next_variable_parent(
        self,
        connection_id: EntityIdVO,
        run_id: EntityIdVO,
        after: str | None,
        current: str | None,
    ) -> str | None:
        """Выбирает следующего полученного родителя, не сохраняя весь список в checkpoint."""
        ...
