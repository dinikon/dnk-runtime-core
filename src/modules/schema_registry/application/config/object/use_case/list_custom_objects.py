from __future__ import annotations

from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO
from src.modules.schema_registry.application.config.object.query import (
    ListCustomObjectsQuery,
)
from src.modules.schema_registry.application.config.object.repository import (
    SchemaConfigRepositoryProtocol,
)


class ListCustomObjectsUseCase:
    """Use case списка кастомных объектов tenant."""

    def __init__(self, repository: SchemaConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, query: ListCustomObjectsQuery) -> list[CustomObjectDTO]:
        """Возвращает список кастомных объектов tenant."""
        return await self._repository.list_objects(query)


__all__ = ["ListCustomObjectsUseCase"]
