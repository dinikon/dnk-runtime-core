from __future__ import annotations

from src.modules.schema_registry.application.config.relation.command import (
    DeleteRelationCommand,
)
from src.modules.schema_registry.application.config.relation.repository import (
    SchemaConfigRelationRepositoryProtocol,
)


class DeleteRelationUseCase:
    """Use case удаления custom relation."""

    def __init__(self, repository: SchemaConfigRelationRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом relations."""
        self._repository = repository

    async def __call__(self, command: DeleteRelationCommand) -> None:
        """Удаляет custom relation."""
        await self._repository.delete_relation(command)


__all__ = ["DeleteRelationUseCase"]
