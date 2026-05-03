from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.config.field.command import (
    AddCustomFieldCommand,
    DeleteCustomFieldCommand,
)
from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO


class SchemaConfigFieldRepositoryProtocol(Protocol):
    """Порт metadata + targeted DDL операций config fields."""

    async def add_field(self, command: AddCustomFieldCommand) -> CustomObjectDTO:
        """Добавляет custom field metadata и физическую колонку."""
        ...

    async def delete_field(self, command: DeleteCustomFieldCommand) -> CustomObjectDTO:
        """Удаляет custom field metadata и физическую колонку."""
        ...


__all__ = ["SchemaConfigFieldRepositoryProtocol"]
