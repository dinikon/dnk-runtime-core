from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.config.object.command import (
    CreateCustomObjectCommand,
    DeleteCustomObjectCommand,
)
from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO
from src.modules.schema_registry.application.config.object.query import (
    CustomObjectByIdQuery,
    ListCustomObjectsQuery,
)


class SchemaConfigRepositoryProtocol(Protocol):
    """Порт metadata + targeted DDL операций runtime objects config."""

    async def list_objects(
        self, query: ListCustomObjectsQuery
    ) -> list[CustomObjectDTO]:
        """Возвращает список runtime objects tenant для config API."""
        ...

    async def describe_object(self, query: CustomObjectByIdQuery) -> CustomObjectDTO:
        """Возвращает schema config runtime object tenant."""
        ...

    async def create_object(
        self, command: CreateCustomObjectCommand
    ) -> CustomObjectDTO:
        """Создает custom object metadata и физическую таблицу."""
        ...

    async def delete_object(self, command: DeleteCustomObjectCommand) -> None:
        """Удаляет custom object metadata и физическую таблицу."""
        ...


__all__ = ["SchemaConfigRepositoryProtocol"]
