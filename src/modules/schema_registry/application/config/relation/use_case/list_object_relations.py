from __future__ import annotations

from src.modules.schema_registry.application.config.relation.dto import RelationDTO
from src.modules.schema_registry.application.config.relation.query import (
    ListObjectRelationsQuery,
)
from src.modules.schema_registry.application.config.relation.repository import (
    SchemaConfigRelationRepositoryProtocol,
)


class ListObjectRelationsUseCase:
    """Use case списка relations object."""

    def __init__(self, repository: SchemaConfigRelationRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом relations."""
        self._repository = repository

    async def __call__(self, query: ListObjectRelationsQuery) -> list[RelationDTO]:
        """Возвращает relations, где object участвует как source или target."""
        return await self._repository.list_object_relations(query)


__all__ = ["ListObjectRelationsUseCase"]
