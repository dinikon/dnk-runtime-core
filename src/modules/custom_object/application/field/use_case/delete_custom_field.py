from __future__ import annotations

from src.modules.custom_object.application.field.command import DeleteCustomFieldCommand
from src.modules.custom_object.application.field.repository import (
    CustomFieldSchemaRepositoryProtocol,
)
from src.modules.custom_object.application.object.dto import CustomObjectDTO


class DeleteCustomFieldUseCase:
    """Use case удаления custom field."""

    def __init__(self, repository: CustomFieldSchemaRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom fields."""
        self._repository = repository

    async def __call__(self, command: DeleteCustomFieldCommand) -> CustomObjectDTO:
        """Удаляет custom field."""
        return await self._repository.delete_field(command)


__all__ = ["DeleteCustomFieldUseCase"]
