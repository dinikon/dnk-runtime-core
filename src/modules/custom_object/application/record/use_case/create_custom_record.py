from __future__ import annotations

from src.modules.custom_object.application.record.command import (
    CreateCustomRecordCommand,
)
from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)


class CreateCustomRecordUseCase:
    """Use case создания runtime-записи кастомного объекта."""

    def __init__(self, repository: CustomRecordRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom records."""
        self._repository = repository

    async def __call__(self, command: CreateCustomRecordCommand) -> CustomRecordDTO:
        """Создает runtime-запись кастомного объекта."""
        return await self._repository.create(command)


__all__ = ["CreateCustomRecordUseCase"]
