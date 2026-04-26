from __future__ import annotations

from src.modules.custom_object.application.field.command import AddCustomFieldCommand
from src.modules.custom_object.application.field.repository import (
    CustomFieldSchemaRepositoryProtocol,
)
from src.modules.custom_object.application.object.dto import CustomObjectDTO


class AddCustomFieldUseCase:
    """Use case добавления custom field."""

    def __init__(self, repository: CustomFieldSchemaRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom fields."""
        self._repository = repository

    async def __call__(self, command: AddCustomFieldCommand) -> CustomObjectDTO:
        """Добавляет custom field."""
        return await self._repository.add_field(command)


__all__ = ["AddCustomFieldUseCase"]
