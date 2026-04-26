from __future__ import annotations

from src.modules.custom_object.application.object.command import (
    DeleteCustomObjectCommand,
)
from src.modules.custom_object.application.object.repository import (
    CustomObjectSchemaRepositoryProtocol,
)


class DeleteCustomObjectUseCase:
    """Use case hard delete кастомного объекта."""

    def __init__(self, repository: CustomObjectSchemaRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, command: DeleteCustomObjectCommand) -> None:
        """Удаляет кастомный объект."""
        await self._repository.delete_object(command)


__all__ = ["DeleteCustomObjectUseCase"]
