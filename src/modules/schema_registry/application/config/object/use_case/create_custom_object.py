from __future__ import annotations

from src.modules.schema_registry.application.config.object.command import (
    CreateCustomObjectCommand,
)
from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO
from src.modules.schema_registry.application.config.object.repository import (
    SchemaConfigRepositoryProtocol,
)


class CreateCustomObjectUseCase:
    """Use case создания кастомного объекта."""

    def __init__(self, repository: SchemaConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, command: CreateCustomObjectCommand) -> CustomObjectDTO:
        """Создает кастомный объект."""
        return await self._repository.create_object(command)


__all__ = ["CreateCustomObjectUseCase"]
