from __future__ import annotations

from typing import Protocol

from src.modules.custom_object.application.field.command import (
    AddCustomFieldCommand,
    DeleteCustomFieldCommand,
)
from src.modules.custom_object.application.object.dto import CustomObjectDTO


class CustomFieldSchemaRepositoryProtocol(Protocol):
    """Порт metadata + targeted DDL операций custom fields."""

    async def add_field(self, command: AddCustomFieldCommand) -> CustomObjectDTO:
        """Добавляет custom field metadata и физическую колонку."""
        ...

    async def delete_field(self, command: DeleteCustomFieldCommand) -> CustomObjectDTO:
        """Удаляет custom field metadata и физическую колонку."""
        ...


__all__ = ["CustomFieldSchemaRepositoryProtocol"]
