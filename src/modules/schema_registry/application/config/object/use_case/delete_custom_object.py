from __future__ import annotations

from src.modules.schema_registry.application.config.object.command import (
    DeleteCustomObjectCommand,
)
from src.modules.schema_registry.application.config.object.repository import (
    SchemaConfigRepositoryProtocol,
)


class DeleteCustomObjectUseCase:
    """Use case hard delete кастомного объекта."""

    def __init__(self, repository: SchemaConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, command: DeleteCustomObjectCommand) -> None:
        """Удаляет кастомный объект."""
        await self._repository.delete_object(command)


__all__ = ["DeleteCustomObjectUseCase"]
