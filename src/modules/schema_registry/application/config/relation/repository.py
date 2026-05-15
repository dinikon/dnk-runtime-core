from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.config.relation.command import (
    CreateRelationCommand,
    DeleteRelationCommand,
)
from src.modules.schema_registry.application.config.relation.dto import RelationDTO
from src.modules.schema_registry.application.config.relation.query import (
    ListObjectRelationsQuery,
)


class SchemaConfigRelationRepositoryProtocol(Protocol):
    """Repository-port config API для custom relations."""

    async def create_relation(self, command: CreateRelationCommand) -> RelationDTO:
        """Создает custom relation."""
        ...

    async def delete_relation(self, command: DeleteRelationCommand) -> None:
        """Удаляет custom relation."""
        ...

    async def list_object_relations(
        self,
        query: ListObjectRelationsQuery,
    ) -> list[RelationDTO]:
        """Возвращает relations, где object участвует как source или target."""
        ...


__all__ = ["SchemaConfigRelationRepositoryProtocol"]
