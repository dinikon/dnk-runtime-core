from __future__ import annotations

from typing import Protocol

from src.modules.custom_object.application.record.command import (
    CreateCustomRecordCommand,
    CustomRecordByIdCommand,
    UpdateCustomRecordCommand,
)
from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.application.record.query import ListCustomRecordsQuery


class CustomRecordRepositoryProtocol(Protocol):
    """Порт runtime CRUD операций custom object records."""

    async def create(self, command: CreateCustomRecordCommand) -> CustomRecordDTO:
        """Создает runtime-запись custom object."""
        ...

    async def get(self, command: CustomRecordByIdCommand) -> CustomRecordDTO:
        """Возвращает runtime-запись custom object."""
        ...

    async def list(self, query: ListCustomRecordsQuery) -> list[CustomRecordDTO]:
        """Возвращает runtime-записи custom object."""
        ...

    async def update(self, command: UpdateCustomRecordCommand) -> CustomRecordDTO:
        """Обновляет runtime-запись custom object."""
        ...

    async def delete(self, command: CustomRecordByIdCommand) -> None:
        """Удаляет runtime-запись custom object."""
        ...


__all__ = ["CustomRecordRepositoryProtocol"]
