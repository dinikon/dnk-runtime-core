from __future__ import annotations

from src.modules.schema_registry.application.config.relation.command import (
    CreateRelationCommand,
)
from src.modules.schema_registry.application.config.relation.dto import RelationDTO
from src.modules.schema_registry.application.config.relation.repository import (
    SchemaConfigRelationRepositoryProtocol,
)


class CreateRelationUseCase:
    """Use case создания custom relation."""

    def __init__(self, repository: SchemaConfigRelationRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом relations."""
        self._repository = repository

    async def __call__(self, command: CreateRelationCommand) -> RelationDTO:
        """Создает custom relation."""
        return await self._repository.create_relation(command)


__all__ = ["CreateRelationUseCase"]
