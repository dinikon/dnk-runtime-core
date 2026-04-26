from __future__ import annotations

from src.modules.custom_object.application.object.dto import CustomObjectDTO
from src.modules.custom_object.application.object.query import ListCustomObjectsQuery
from src.modules.custom_object.application.object.repository import (
    CustomObjectSchemaRepositoryProtocol,
)


class ListCustomObjectsUseCase:
    """Use case списка кастомных объектов tenant."""

    def __init__(self, repository: CustomObjectSchemaRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, query: ListCustomObjectsQuery) -> list[CustomObjectDTO]:
        """Возвращает список кастомных объектов tenant."""
        return await self._repository.list_objects(query)


__all__ = ["ListCustomObjectsUseCase"]
