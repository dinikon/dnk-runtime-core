from __future__ import annotations

from src.modules.schema_registry.application.config.field.command import (
    DeleteCustomFieldCommand,
)
from src.modules.schema_registry.application.config.field.repository import (
    SchemaConfigFieldRepositoryProtocol,
)
from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO


class DeleteCustomFieldUseCase:
    """Use case удаления custom field."""

    def __init__(self, repository: SchemaConfigFieldRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom fields."""
        self._repository = repository

    async def __call__(self, command: DeleteCustomFieldCommand) -> CustomObjectDTO:
        """Удаляет custom field."""
        return await self._repository.delete_field(command)


__all__ = ["DeleteCustomFieldUseCase"]
