from __future__ import annotations

from src.modules.custom_object.application.object.command import (
    CreateCustomObjectCommand,
)
from src.modules.custom_object.application.object.dto import CustomObjectDTO
from src.modules.custom_object.application.object.repository import (
    CustomObjectSchemaRepositoryProtocol,
)


class CreateCustomObjectUseCase:
    """Use case создания кастомного объекта."""

    def __init__(self, repository: CustomObjectSchemaRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, command: CreateCustomObjectCommand) -> CustomObjectDTO:
        """Создает кастомный объект."""
        return await self._repository.create_object(command)


__all__ = ["CreateCustomObjectUseCase"]
