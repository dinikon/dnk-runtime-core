from __future__ import annotations

from typing import Protocol

from src.modules.custom_object.application.object.command import (
    CreateCustomObjectCommand,
    DeleteCustomObjectCommand,
)
from src.modules.custom_object.application.object.dto import CustomObjectDTO
from src.modules.custom_object.application.object.query import (
    CustomObjectByIdQuery,
    ListCustomObjectsQuery,
)


class CustomObjectSchemaRepositoryProtocol(Protocol):
    """Порт metadata + targeted DDL операций кастомных объектов."""

    async def list_objects(
        self, query: ListCustomObjectsQuery
    ) -> list[CustomObjectDTO]:
        """Возвращает список кастомных объектов tenant."""
        ...

    async def describe_object(self, query: CustomObjectByIdQuery) -> CustomObjectDTO:
        """Возвращает схему кастомного объекта tenant."""
        ...

    async def create_object(
        self, command: CreateCustomObjectCommand
    ) -> CustomObjectDTO:
        """Создает metadata и физическую таблицу кастомного объекта."""
        ...

    async def delete_object(self, command: DeleteCustomObjectCommand) -> None:
        """Удаляет metadata и физическую таблицу кастомного объекта."""
        ...


__all__ = ["CustomObjectSchemaRepositoryProtocol"]
